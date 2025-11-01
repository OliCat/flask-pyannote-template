#!/usr/bin/env python3
"""
Module pour isoler pyannote MPS dans un processus séparé
Permet d'utiliser MPS avec Flask/Gunicorn sans crashs

Utilisation:
    from pyannote_isolated import run_diarization_isolated
    
    result = run_diarization_isolated(
        audio_file_path="/path/to/audio.wav",
        use_mps=True,
        batch_size=16,
        timeout=600
    )
"""

import multiprocessing
import json
import tempfile
from pathlib import Path
import subprocess
import os
import gc
import time

# Import conditionnel pour éviter erreurs si pyannote non disponible
try:
    from pyannote_mps_helper import create_pyannote_pipeline_safe, process_with_memory_management
    import torch
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    print("⚠️ pyannote_mps_helper non disponible")


def diarize_isolated(audio_file_path, output_json_path, use_mps=True, batch_size=16):
    """
    Fonction exécutée dans le processus isolé pour la diarisation.
    
    Cette fonction est isolée dans un processus séparé pour éviter
    les problèmes de partage mémoire MPS avec les workers Gunicorn.
    
    Args:
        audio_file_path: Chemin vers le fichier audio
        output_json_path: Chemin vers le fichier JSON de sortie
        use_mps: Utiliser MPS si disponible
        batch_size: Taille de batch pour l'embedding
    
    Returns:
        dict: Résultats de la diarisation ou None si erreur
    """
    if not PYANNOTE_AVAILABLE:
        result = {
            'success': False,
            'error': 'pyannote_mps_helper non disponible'
        }
        with open(output_json_path, 'w') as f:
            json.dump(result, f, indent=2)
        return None
    
    try:
        print(f"🔧 [Processus isolé PID={os.getpid()}] Initialisation du pipeline MPS...")
        
        # Créer le pipeline dans le processus isolé
        pipeline = create_pyannote_pipeline_safe(
            model_name="pyannote/speaker-diarization-3.1",
            use_auth_token=True,
            prefer_mps=use_mps,
            embedding_batch_size=batch_size
        )
        
        # Vérifier le device utilisé
        device = torch.device('mps') if use_mps and torch.backends.mps.is_available() else torch.device('cpu')
        device_str = str(device)
        
        if hasattr(pipeline, '_segmentation') and hasattr(pipeline._segmentation, 'model'):
            try:
                seg_model = pipeline._segmentation.model
                if hasattr(seg_model, 'parameters'):
                    first_param = next(iter(seg_model.parameters()))
                    device_str = str(first_param.device)
            except:
                pass
        
        print(f"✅ [Processus isolé] Pipeline initialisé sur {device_str}")
        
        # Conversion audio si nécessaire (16kHz mono pour Pyannote)
        audio_path = Path(audio_file_path)
        converted_path = str(audio_path.with_suffix('_16k.wav'))
        
        print(f"🔄 [Processus isolé] Conversion audio 16kHz mono...")
        subprocess.run([
            'ffmpeg', '-i', audio_file_path,
            '-ar', '16000', '-ac', '1', '-f', 'wav',
            '-y', converted_path
        ], check=True, capture_output=True)
        print(f"✅ [Processus isolé] Conversion terminée")
        
        print(f"🎯 [Processus isolé] Début de la diarisation sur {device_str}...")
        start_time = time.time()
        
        # Traitement avec gestion mémoire
        diarization = process_with_memory_management(
            pipeline, 
            converted_path, 
            device
        )
        
        elapsed = time.time() - start_time
        
        # Extraire les segments
        speaker_segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker_segments.append({
                'start': float(turn.start),
                'end': float(turn.end),
                'speaker': speaker
            })
        
        speakers = sorted(list(set(seg['speaker'] for seg in speaker_segments)))
        
        print(f"✅ [Processus isolé] Diarisation terminée en {elapsed:.1f}s")
        print(f"   - {len(speakers)} locuteurs: {', '.join(speakers)}")
        print(f"   - {len(speaker_segments)} segments")
        
        # Sauvegarder les résultats
        result = {
            'success': True,
            'speakers': speakers,
            'segments': speaker_segments,
            'total_segments': len(speaker_segments),
            'device_used': device_str,
            'processing_time': elapsed
        }
        
        with open(output_json_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Nettoyage
        if os.path.exists(converted_path):
            os.unlink(converted_path)
        
        # Nettoyage mémoire GPU si MPS
        if device.type == 'mps':
            torch.mps.empty_cache()
        gc.collect()
        
        return result
        
    except RuntimeError as e:
        if 'out of memory' in str(e).lower() or 'memory' in str(e).lower():
            print(f"⚠️ [Processus isolé] Erreur OOM détectée: {e}")
            print("🔄 [Processus isolé] Tentative fallback vers CPU...")
            
            try:
                # Réessayer avec CPU
                pipeline.to(torch.device('cpu'))
                device_str = 'cpu'
                
                diarization = pipeline(converted_path)
                
                # Extraire les segments
                speaker_segments = []
                for turn, _, speaker in diarization.itertracks(yield_label=True):
                    speaker_segments.append({
                        'start': float(turn.start),
                        'end': float(turn.end),
                        'speaker': speaker
                    })
                
                speakers = sorted(list(set(seg['speaker'] for seg in speaker_segments)))
                
                result = {
                    'success': True,
                    'speakers': speakers,
                    'segments': speaker_segments,
                    'total_segments': len(speaker_segments),
                    'device_used': 'cpu',
                    'fallback_cpu': True,
                    'error': str(e)
                }
                
                with open(output_json_path, 'w') as f:
                    json.dump(result, f, indent=2)
                
                # Nettoyage
                if os.path.exists(converted_path):
                    os.unlink(converted_path)
                
                return result
            except Exception as fallback_error:
                print(f"❌ [Processus isolé] Erreur fallback CPU: {fallback_error}")
                error = fallback_error
        else:
            error = e
        
        print(f"❌ [Processus isolé] Erreur: {error}")
        import traceback
        traceback.print_exc()
        
        # Sauvegarder l'erreur
        result = {
            'success': False,
            'error': str(error)
        }
        with open(output_json_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        return None


def run_diarization_isolated(audio_file_path, use_mps=True, batch_size=16, timeout=600):
    """
    Lance la diarisation dans un processus isolé.
    
    Cette fonction lance un nouveau processus Python pour exécuter
    la diarisation, isolant ainsi MPS du worker Gunicorn parent.
    
    Args:
        audio_file_path: Chemin vers le fichier audio
        use_mps: Utiliser MPS si disponible (défaut: True)
        batch_size: Taille de batch pour l'embedding (défaut: 16)
        timeout: Timeout en secondes (défaut: 600 = 10 minutes)
    
    Returns:
        dict: Résultats de la diarisation ou None si erreur/timeout
        
    Exemple:
        >>> result = run_diarization_isolated("/path/to/audio.wav")
        >>> if result and result.get('success'):
        ...     print(f"Locuteurs: {result['speakers']}")
        ...     print(f"Segments: {result['total_segments']}")
    """
    if not PYANNOTE_AVAILABLE:
        print("❌ [Worker] pyannote non disponible")
        return None
    
    # Créer un fichier temporaire pour la communication
    output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    output_path = output_file.name
    output_file.close()
    
    try:
        # Créer un processus isolé
        process = multiprocessing.Process(
            target=diarize_isolated,
            args=(audio_file_path, output_path, use_mps, batch_size),
            name='pyannote-diarization'
        )
        
        print(f"🚀 [Worker PID={os.getpid()}] Lancement du processus isolé pour diarisation...")
        print(f"   - Audio: {audio_file_path}")
        print(f"   - MPS: {'Activé' if use_mps else 'Désactivé'}")
        print(f"   - Batch size: {batch_size}")
        print(f"   - Timeout: {timeout}s")
        
        start_time = time.time()
        
        process.start()
        process.join(timeout=timeout)  # Attendre avec timeout
        
        elapsed = time.time() - start_time
        
        # Vérifier si le processus s'est terminé
        if process.is_alive():
            print(f"⏱️ [Worker] Timeout après {timeout}s - arrêt du processus...")
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                print(f"⚠️ [Worker] Processus encore actif - kill forcé...")
                process.kill()
                process.join(timeout=2)
            
            # Nettoyer et retourner None
            if os.path.exists(output_path):
                os.unlink(output_path)
            return None
        
        # Vérifier le code de sortie
        if process.exitcode != 0:
            print(f"⚠️ [Worker] Processus terminé avec code d'erreur: {process.exitcode}")
        
        # Lire les résultats
        if Path(output_path).exists():
            try:
                with open(output_path, 'r') as f:
                    result = json.load(f)
                
                if result.get('success'):
                    print(f"✅ [Worker] Diarisation terminée en {elapsed:.1f}s")
                    print(f"   - Device utilisé: {result.get('device_used', 'unknown')}")
                    if result.get('fallback_cpu'):
                        print(f"   ⚠️ Fallback CPU utilisé (OOM sur MPS)")
                    return result
                else:
                    print(f"❌ [Worker] Erreur dans le processus isolé: {result.get('error')}")
                    return None
            except json.JSONDecodeError as e:
                print(f"❌ [Worker] Erreur lecture JSON: {e}")
                return None
        
        return None
        
    except Exception as e:
        print(f"❌ [Worker] Erreur lors du lancement du processus: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        # Nettoyer le fichier temporaire
        if os.path.exists(output_path):
            try:
                os.unlink(output_path)
            except:
                pass


if __name__ == '__main__':
    """
    Test standalone de la fonction isolée
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pyannote_isolated.py <audio_file> [use_mps] [batch_size]")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    use_mps = sys.argv[2].lower() == 'true' if len(sys.argv) > 2 else True
    batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    
    print("=" * 60)
    print("🧪 Test standalone de diarisation isolée")
    print("=" * 60)
    print(f"Audio: {audio_file}")
    print(f"MPS: {use_mps}")
    print(f"Batch size: {batch_size}")
    print()
    
    result = run_diarization_isolated(
        audio_file,
        use_mps=use_mps,
        batch_size=batch_size,
        timeout=600
    )
    
    if result and result.get('success'):
        print("\n" + "=" * 60)
        print("✅ Succès !")
        print("=" * 60)
        print(f"Locuteurs: {result['speakers']}")
        print(f"Segments: {result['total_segments']}")
        print(f"Device: {result['device_used']}")
        if result.get('processing_time'):
            print(f"Temps: {result['processing_time']:.1f}s")
    else:
        print("\n" + "=" * 60)
        print("❌ Échec")
        print("=" * 60)
        if result:
            print(f"Erreur: {result.get('error')}")
        sys.exit(1)

