#!/usr/bin/env python3
"""
Helper pour utiliser MPS de manière stable avec pyannote.audio
Basé sur les meilleures pratiques pour éviter les crashs de mémoire

Références:
- https://apxml.com/posts/pytorch-macos-metal-gpu
- Problèmes de mémoire MPS documentés dans la communauté PyTorch
"""

import torch
from pyannote.audio import Pipeline
import gc
import warnings


def get_safe_device(prefer_mps=False, fallback_to_cpu=True):
    """
    Détermine le device le plus sûr à utiliser avec pyannote.
    
    Args:
        prefer_mps: Si True, essaie d'utiliser MPS si disponible
        fallback_to_cpu: Si True, retourne CPU si MPS pose problème
    
    Returns:
        torch.device: Device à utiliser
    """
    if prefer_mps and hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        # Vérifier que MPS est vraiment fonctionnel
        try:
            # Test rapide: créer un petit tenseur sur MPS
            test_tensor = torch.randn(10, 10).to('mps')
            _ = test_tensor * 2  # Opération simple
            del test_tensor
            torch.mps.empty_cache()  # Nettoyer
            gc.collect()
            return torch.device('mps')
        except Exception as e:
            warnings.warn(f"MPS disponible mais test échoué: {e}. Fallback vers CPU.")
            if fallback_to_cpu:
                return torch.device('cpu')
    
    # CPU par défaut (le plus stable)
    return torch.device('cpu')


def create_pyannote_pipeline_safe(
    model_name="pyannote/speaker-diarization-3.1",
    use_auth_token=True,
    prefer_mps=False,
    embedding_batch_size=None
):
    """
    Crée un pipeline pyannote de manière sûre avec gestion du device.
    
    Args:
        model_name: Nom du modèle pyannote
        use_auth_token: Token HuggingFace
        prefer_mps: Si True, essaie d'utiliser MPS
        embedding_batch_size: Taille de batch pour l'embedding (plus petit = moins de mémoire)
    
    Returns:
        Pipeline: Pipeline pyannote configuré
    """
    device = get_safe_device(prefer_mps=prefer_mps)
    
    print(f"🔧 Création du pipeline pyannote sur device: {device}")
    
    # Créer le pipeline
    pipeline = Pipeline.from_pretrained(
        model_name,
        use_auth_token=use_auth_token
    )
    
    # Configurations pour MPS si nécessaire
    if device.type == 'mps':
        print("🍎 Configuration MPS activée")
        print("   ⚠️ Mode expérimental - en cas de crash, utiliser CPU")
        
        # Réduire la taille de batch par défaut pour économiser la mémoire
        # Les tailles de 16-64 sont recommandées pour MPS
        if embedding_batch_size is None:
            embedding_batch_size = 16  # Plus petit que la valeur par défaut
            print(f"   📦 Taille de batch réduite à {embedding_batch_size} pour MPS")
        
        if hasattr(pipeline, 'embedding_batch_size'):
            pipeline.embedding_batch_size = embedding_batch_size
    
    # Déplacer le pipeline sur le device choisi
    try:
        pipeline.to(device)
        print(f"✅ Pipeline déplacé vers {device}")
        
        # Vérification: s'assurer que les modèles sont bien sur le bon device
        if hasattr(pipeline, '_segmentation') and hasattr(pipeline._segmentation, 'model'):
            seg_model = pipeline._segmentation.model
            if hasattr(seg_model, 'parameters'):
                first_param = next(iter(seg_model.parameters()))
                actual_device = str(first_param.device)
                if actual_device != str(device):
                    print(f"   ⚠️ Avertissement: device attendu {device}, détecté {actual_device}")
                else:
                    print(f"   ✓ Vérification device: {actual_device}")
        
        return pipeline
    
    except Exception as e:
        print(f"❌ Erreur lors du déplacement vers {device}: {e}")
        if device.type == 'mps':
            print("   🔄 Tentative de fallback vers CPU...")
            device = torch.device('cpu')
            pipeline.to(device)
            print(f"   ✅ Fallback réussi: utilisation de CPU")
        return pipeline


def process_with_memory_management(pipeline, audio_file, device):
    """
    Traite un fichier audio avec gestion proactive de la mémoire.
    Utile pour éviter les crashs MPS dus aux problèmes de mémoire.
    """
    # Nettoyer avant le traitement
    if device.type == 'mps':
        torch.mps.empty_cache()
    elif device.type == 'cuda':
        torch.cuda.empty_cache()
    gc.collect()
    
    try:
        # Traitement
        result = pipeline(audio_file)
        
        # Nettoyer après le traitement
        if device.type == 'mps':
            torch.mps.empty_cache()
        elif device.type == 'cuda':
            torch.cuda.empty_cache()
        gc.collect()
        
        return result
    
    except RuntimeError as e:
        if 'out of memory' in str(e).lower() or 'memory' in str(e).lower():
            print(f"⚠️ Erreur de mémoire détectée: {e}")
            if device.type == 'mps':
                print("   💡 Suggestions:")
                print("      - Réduire embedding_batch_size")
                print("      - Utiliser CPU à la place (plus stable)")
                print("      - Traiter des fichiers audio plus courts")
        raise


# Exemple d'utilisation
if __name__ == "__main__":
    print("=" * 60)
    print("🔧 Helper pour pyannote avec MPS sécurisé")
    print("=" * 60)
    
    # Test 1: CPU (le plus sûr)
    print("\n1️⃣ Test avec CPU (mode recommandé):")
    try:
        pipeline_cpu = create_pyannote_pipeline_safe(prefer_mps=False)
        print("   ✅ Pipeline CPU créé avec succès")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    # Test 2: MPS si disponible (expérimental)
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        print("\n2️⃣ Test avec MPS (mode expérimental):")
        try:
            pipeline_mps = create_pyannote_pipeline_safe(
                prefer_mps=True,
                embedding_batch_size=16  # Taille réduite pour MPS
            )
            print("   ✅ Pipeline MPS créé avec succès")
            print("   ⚠️ Note: En cas de crash, utiliser CPU")
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            print("   💡 Recommandation: Utiliser CPU (mode préféré)")
    else:
        print("\n2️⃣ MPS non disponible sur ce système")
    
    print("\n" + "=" * 60)
    print("💡 RECOMMANDATIONS:")
    print("   - CPU: Le plus stable, recommandé pour la production")
    print("   - MPS: Plus rapide mais peut crasher (mode expérimental)")
    print("   - En cas de crash MPS: réduire embedding_batch_size ou utiliser CPU")
    print("=" * 60)

