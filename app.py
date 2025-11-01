#!/usr/bin/env python3
"""
Application Flask pour diarisation avec Pyannote MPS isolé

Template d'application Flask/Gunicorn avec isolation MPS via multiprocessing.
Permet l'utilisation de MPS avec plusieurs workers Gunicorn sans crashs.
"""

from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import tempfile
import os
from pathlib import Path
import time
import logging
from datetime import datetime

# Import du module d'isolation
from pyannote_isolated import run_diarization_isolated

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB max
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
app.config['ALLOWED_EXTENSIONS'] = {'wav', 'mp3', 'm4a', 'flac', 'aac', 'ogg'}

def allowed_file(filename):
    """Vérifie si l'extension du fichier est autorisée"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/health', methods=['GET'])
def health():
    """Endpoint de santé de l'application"""
    import multiprocessing
    import torch
    
    info = {
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'workers': os.environ.get('GUNICORN_WORKERS', '1'),
        'mps_available': torch.backends.mps.is_available() if hasattr(torch.backends, 'mps') else False,
        'cpu_count': multiprocessing.cpu_count(),
        'version': '1.0.0'
    }
    
    return jsonify(info)


@app.route('/api/v1/diarize', methods=['POST'])
def diarize():
    """
    Endpoint principal de diarisation
    
    POST /api/v1/diarize
    Content-Type: multipart/form-data
    
    Form fields:
    - audio: fichier audio (obligatoire)
    - use_mps: true/false (optionnel, défaut: true)
    - batch_size: nombre (optionnel, défaut: 16)
    - timeout: nombre secondes (optionnel, défaut: 600)
    
    Returns:
        JSON avec résultats de diarisation
    """
    start_time = time.time()
    
    try:
        # Vérifier la présence du fichier
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Fichier audio manquant. Utilisez le champ "audio" dans form-data.'
            }), 400
        
        audio_file = request.files['audio']
        
        if audio_file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Nom de fichier vide'
            }), 400
        
        if not allowed_file(audio_file.filename):
            return jsonify({
                'success': False,
                'error': f'Extension non autorisée. Extensions autorisées: {", ".join(app.config["ALLOWED_EXTENSIONS"])}'
            }), 400
        
        # Récupérer les paramètres optionnels
        use_mps = request.form.get('use_mps', 'true').lower() == 'true'
        batch_size = int(request.form.get('batch_size', '16'))
        timeout = int(request.form.get('timeout', '600'))
        
        logger.info(f"🎯 Nouvelle requête de diarisation")
        logger.info(f"   Fichier: {audio_file.filename}")
        logger.info(f"   MPS: {use_mps}")
        logger.info(f"   Batch size: {batch_size}")
        logger.info(f"   Timeout: {timeout}s")
        
        # Sauvegarder temporairement le fichier
        filename = secure_filename(audio_file.filename)
        temp_path = None
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{filename}') as tmp:
                audio_file.save(tmp.name)
                temp_path = tmp.name
            
            logger.info(f"📁 Fichier sauvegardé: {temp_path}")
            
            # Lancer la diarisation dans un processus isolé
            logger.info(f"🚀 Lancement du processus isolé pour diarisation...")
            
            result = run_diarization_isolated(
                temp_path,
                use_mps=use_mps,
                batch_size=batch_size,
                timeout=timeout
            )
            
            elapsed = time.time() - start_time
            
            if result and result.get('success'):
                logger.info(f"✅ Diarisation réussie en {elapsed:.1f}s")
                
                response = {
                    'success': True,
                    'request_time': elapsed,
                    'processing_time': result.get('processing_time', 0),
                    'speakers': result.get('speakers', []),
                    'segments': result.get('segments', []),
                    'total_segments': result.get('total_segments', 0),
                    'device_used': result.get('device_used', 'unknown'),
                    'fallback_cpu': result.get('fallback_cpu', False)
                }
                
                if result.get('fallback_cpu'):
                    logger.warning("⚠️ Fallback CPU utilisé (OOM sur MPS)")
                    response['warning'] = 'OOM sur MPS, traité sur CPU'
                
                return jsonify(response), 200
            else:
                logger.error(f"❌ Échec de la diarisation")
                error_msg = result.get('error', 'Erreur inconnue') if result else 'Timeout ou erreur inconnue'
                
                return jsonify({
                    'success': False,
                    'error': error_msg,
                    'request_time': elapsed
                }), 500
        
        finally:
            # Nettoyer le fichier temporaire
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                    logger.debug(f"🧹 Fichier temporaire supprimé: {temp_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Erreur suppression fichier: {e}")
    
    except ValueError as e:
        logger.error(f"❌ Erreur de validation: {e}")
        return jsonify({
            'success': False,
            'error': f'Erreur de paramètre: {str(e)}'
        }), 400
    
    except Exception as e:
        elapsed = time.time() - start_time
        logger.exception(f"❌ Erreur lors de la diarisation: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'request_time': elapsed
        }), 500


@app.route('/api/v1/diarize/info', methods=['GET'])
def diarize_info():
    """Informations sur l'endpoint de diarisation"""
    return jsonify({
        'endpoint': '/api/v1/diarize',
        'method': 'POST',
        'content_type': 'multipart/form-data',
        'required_fields': {
            'audio': 'Fichier audio (wav, mp3, m4a, flac, aac, ogg)'
        },
        'optional_fields': {
            'use_mps': 'true/false (défaut: true) - Utiliser MPS si disponible',
            'batch_size': 'nombre (défaut: 16) - Taille de batch pour embedding',
            'timeout': 'nombre secondes (défaut: 600) - Timeout du processus isolé'
        },
        'example': {
            'curl': 'curl -X POST -F "audio=@file.wav" -F "use_mps=true" http://localhost:5000/api/v1/diarize'
        }
    })


@app.errorhandler(413)
def request_entity_too_large(error):
    """Gestion des fichiers trop volumineux"""
    return jsonify({
        'success': False,
        'error': 'Fichier trop volumineux. Taille maximale: 500 MB'
    }), 413


@app.errorhandler(404)
def not_found(error):
    """Gestion des routes non trouvées"""
    return jsonify({
        'success': False,
        'error': 'Route non trouvée'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Gestion des erreurs internes"""
    logger.exception("Erreur interne serveur")
    return jsonify({
        'success': False,
        'error': 'Erreur interne du serveur'
    }), 500


if __name__ == '__main__':
    # Mode développement
    logger.info("🚀 Démarrage en mode développement...")
    logger.info("💡 Pour production: gunicorn -c gunicorn_config.py app:app")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )

