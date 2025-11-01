# Flask Pyannote Template 🚀

Template d'application Flask/Gunicorn pour la diarisation audio avec Pyannote, utilisant **MPS (GPU Apple Silicon) isolé via multiprocessing**.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Solution innovante** pour utiliser MPS avec Gunicorn multi-workers sans crashs mémoire, via isolation par processus séparé.

## ✨ Fonctionnalités

- ✅ **Diarisation haute performance** avec Pyannote
- ✅ **Support MPS** (GPU Apple Silicon) via processus isolé
- ✅ **Multi-workers Gunicorn** sans crashs mémoire
- ✅ **Fallback CPU automatique** en cas d'OOM
- ✅ **API REST** propre et documentée
- ✅ **Gestion d'erreurs** robuste
- ✅ **Production-ready** avec configuration Gunicorn

## 🚀 Installation rapide

### 1. Cloner et installer les dépendances

```bash
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt
```

### 2. Configuration HuggingFace (pour Pyannote)

```bash
# Installer huggingface-cli
pip install huggingface_hub

# Se connecter avec votre token
huggingface-cli login
```

Acceptez les conditions d'utilisation:
- [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
- [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)

### 3. Modules nécessaires ✅

Les modules suivants sont **déjà inclus** dans ce template:
- ✅ `pyannote_isolated.py` - Module d'isolation MPS
- ✅ `pyannote_mps_helper.py` - Helper MPS sécurisé

**Note:** Ces fichiers sont inclus, plus besoin de les copier depuis un autre projet !

## 🎯 Utilisation

### Mode développement

```bash
python app.py
```

L'application démarre sur `http://localhost:5000`

### Mode production avec Gunicorn

```bash
# Configuration standard (plusieurs workers, CPU)
gunicorn -c gunicorn_config.py app:app

# Ou avec variables d'environnement
GUNICORN_WORKERS=4 gunicorn -c gunicorn_config.py app:app

# Sur un port spécifique
BIND=0.0.0.0:8000 gunicorn -c gunicorn_config.py app:app
```

## 📡 API

### Health Check

```bash
GET /health
```

Retourne l'état de l'application et les informations système.

### Diarisation

```bash
POST /api/v1/diarize
Content-Type: multipart/form-data
```

**Paramètres obligatoires:**
- `audio`: Fichier audio (wav, mp3, m4a, flac, aac, ogg)

**Paramètres optionnels:**
- `use_mps`: `true`/`false` (défaut: `true`) - Utiliser MPS si disponible
- `batch_size`: nombre (défaut: `16`) - Taille de batch pour embedding
- `timeout`: nombre secondes (défaut: `600`) - Timeout du processus isolé

**Exemple avec curl:**

```bash
curl -X POST \
  -F "audio=@your_audio.wav" \
  -F "use_mps=true" \
  -F "batch_size=16" \
  http://localhost:5000/api/v1/diarize
```

**Exemple avec Python:**

```python
import requests

files = {'audio': open('audio.wav', 'rb')}
data = {'use_mps': 'true', 'batch_size': '16'}

response = requests.post('http://localhost:5000/api/v1/diarize', 
                        files=files, data=data)
result = response.json()

if result['success']:
    print(f"Locuteurs: {result['speakers']}")
    print(f"Segments: {result['total_segments']}")
    print(f"Device utilisé: {result['device_used']}")
```

**Réponse JSON:**

```json
{
  "success": true,
  "request_time": 75.3,
  "processing_time": 70.2,
  "speakers": ["SPEAKER_00", "SPEAKER_01"],
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "speaker": "SPEAKER_00"
    },
    ...
  ],
  "total_segments": 42,
  "device_used": "mps:0"
}
```

### Informations API

```bash
GET /api/v1/diarize/info
```

Retourne la documentation de l'endpoint de diarisation.

## ⚙️ Configuration

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `GUNICORN_WORKERS` | Nombre de workers Gunicorn | Nombre de CPU |
| `BIND` | Interface et port | `0.0.0.0:5000` |
| `ACCESS_LOG` | Fichier de log accès | `-` (stdout) |
| `ERROR_LOG` | Fichier de log erreurs | `-` (stderr) |
| `LOG_LEVEL` | Niveau de log | `info` |
| `PID_FILE` | Fichier PID Gunicorn | None |

### Configuration de l'application

Modifier `app.py` pour ajuster:
- `MAX_CONTENT_LENGTH`: Taille max des fichiers (défaut: 500 MB)
- `ALLOWED_EXTENSIONS`: Extensions audio autorisées

## 📊 Performances

Pour un fichier de **30 minutes**:

| Étape | Device | Temps |
|-------|--------|-------|
| Diarisation | **MPS** | **~1 min 10 sec** ⚡ |
| Diarisation | CPU | ~35 minutes 🐢 |

**Gain MPS vs CPU**: **30x plus rapide** !

## 🔧 Architecture

```
Gunicorn Workers (multi)
    │
    ├─> Flask Application
    │   └─> API Routes
    │
    └─> Processus isolé (multiprocessing)
        └─> Pyannote MPS
            ├─> Isolation mémoire complète
            ├─> Pas de partage avec worker
            └─> Communication via JSON
```

## 🛡️ Sécurité

- Validation des extensions de fichiers
- Limite de taille des fichiers (500 MB)
- Nettoyage automatique des fichiers temporaires
- Timeout sur les processus isolés
- Gestion d'erreurs complète

## 🐛 Débogage

### Logs

Les logs sont affichés dans la console (ou fichiers si configurés).

Niveaux de log:
- `INFO`: Opérations normales
- `WARNING`: Avertissements (ex: fallback CPU)
- `ERROR`: Erreurs de traitement
- `DEBUG`: Détails supplémentaires

### Problèmes courants

**OOM sur MPS:**
- Réduire `batch_size` (essayer 8, 4)
- Le fallback CPU se déclenche automatiquement

**Timeout:**
- Augmenter `timeout` dans la requête (max recommandé: 1800s = 30 min)

**Fichier trop volumineux:**
- Augmenter `MAX_CONTENT_LENGTH` dans `app.py`

## 📚 Documentation

- [MPS_ISOLATION_GUIDE.md](../MPS_ISOLATION_GUIDE.md) - Guide complet sur l'isolation MPS
- [FLASK_GUNICORN_MPS_GUIDE.md](../FLASK_GUNICORN_MPS_GUIDE.md) - Guide Flask/Gunicorn avec MPS

## 🚀 Déploiement

### Production

1. **Utiliser Gunicorn** (jamais le serveur de développement Flask)
2. **Configurer les logs** (fichiers au lieu de stdout)
3. **Utiliser un reverse proxy** (Nginx, Caddy)
4. **Surveiller les ressources** (mémoire, CPU, GPU)
5. **Configurer les limites** (timeout, taille fichiers)

### Exemple avec Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 600s;
    }
}
```

## 📝 Licence

MIT License - Libre d'utilisation et modification

Voir [LICENSE](LICENSE) pour plus de détails.

## 🙏 Remerciements

Solution d'isolation MPS développée pour résoudre les crashs mémoire avec Gunicorn.

## 🤝 Contribuer

Les contributions sont les bienvenues ! Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour les guidelines.

## ⭐ Star le projet

Si ce template vous est utile, pensez à ⭐ star le projet sur GitHub !

## 📧 Support

Pour les questions ou problèmes, ouvrez une issue sur GitHub.

---

**Template créé pour faciliter l'intégration de Pyannote MPS dans Flask/Gunicorn** 🚀

