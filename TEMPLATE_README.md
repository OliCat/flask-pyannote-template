# Template Flask Pyannote - Guide d'utilisation

## 📦 Structure du template

```
flask_pyannote_template/
├── app.py                  # Application Flask principale
├── gunicorn_config.py      # Configuration Gunicorn
├── requirements.txt         # Dépendances Python
├── README.md               # Documentation complète
├── install.sh              # Script d'installation
├── .gitignore              # Fichiers à ignorer
└── docker-compose.yml.example  # Exemple Docker Compose
```

## ✅ Modules inclus

Les modules suivants sont **déjà inclus** dans ce template:
- ✅ `pyannote_isolated.py` - Isolation MPS via multiprocessing
- ✅ `pyannote_mps_helper.py` - Helper MPS sécurisé

**Plus besoin de copier depuis un autre projet !** 🎉

## ⚡ Installation rapide

### Option 1: Script automatique

```bash
chmod +x install.sh
./install.sh
```

### Option 2: Installation manuelle

```bash
# Créer environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# ou venv\Scripts\activate  # Windows

# Installer dépendances
pip install -r requirements.txt

# Copier les modules nécessaires
cp ../pyannote_isolated.py .
cp ../pyannote_mps_helper.py .

# Configurer HuggingFace
huggingface-cli login
```

## 🚀 Utilisation

### Mode développement

```bash
python app.py
```

### Mode production

```bash
gunicorn -c gunicorn_config.py app:app
```

## 📡 Test de l'API

### Health check

```bash
curl http://localhost:5000/health
```

### Diarisation

```bash
curl -X POST \
  -F "audio=@test.wav" \
  -F "use_mps=true" \
  http://localhost:5000/api/v1/diarize
```

## 🎯 Fonctionnalités incluses

✅ **API REST complète**
- Endpoint de santé (`/health`)
- Endpoint de diarisation (`/api/v1/diarize`)
- Documentation API (`/api/v1/diarize/info`)

✅ **Gestion d'erreurs**
- Validation des fichiers
- Gestion des erreurs OOM
- Fallback CPU automatique
- Timeout configurable

✅ **Configuration production**
- Gunicorn configuré
- Multi-workers supporté
- Logging configuré
- Variables d'environnement

✅ **Sécurité**
- Validation des extensions
- Limite de taille fichiers
- Nettoyage automatique
- Gestion des erreurs

## 🔧 Personnalisation

### Modifier la taille max des fichiers

Éditer `app.py`:
```python
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # 1 GB
```

### Modifier les extensions autorisées

Éditer `app.py`:
```python
app.config['ALLOWED_EXTENSIONS'] = {'wav', 'mp3', 'm4a', 'flac'}
```

### Modifier le nombre de workers

Éditer `gunicorn_config.py` ou utiliser variable d'environnement:
```bash
GUNICORN_WORKERS=4 gunicorn -c gunicorn_config.py app:app
```

## 📊 Performances

Avec MPS isolé:
- **Diarisation 30 min**: ~1 min 10 sec
- **CPU équivalent**: ~35 minutes
- **Gain**: 30x plus rapide

## 🐛 Débogage

### Logs

Les logs sont affichés dans la console. Pour production, configurer dans `gunicorn_config.py`:
```python
accesslog = '/var/log/app/access.log'
errorlog = '/var/log/app/error.log'
```

### Problèmes courants

**ImportError: pyannote_isolated**
- Vérifier que `pyannote_isolated.py` est dans le même répertoire que `app.py`

**ImportError: pyannote_mps_helper**
- Vérifier que `pyannote_mps_helper.py` est dans le même répertoire

**OOM sur MPS**
- Réduire `batch_size` (essayer 8 ou 4)
- Le fallback CPU se déclenche automatiquement

**ffmpeg non trouvé**
- Installer ffmpeg: `brew install ffmpeg` (Mac) ou `sudo apt install ffmpeg` (Linux)

## 📚 Documentation complète

Voir `README.md` pour la documentation complète de l'API et de l'utilisation.

## 🎉 Prêt à l'emploi !

Ce template est prêt à être utilisé en production. Il inclut:
- ✅ Toute la gestion MPS isolée
- ✅ Configuration Gunicorn optimale
- ✅ API REST complète
- ✅ Gestion d'erreurs robuste
- ✅ Documentation complète

**Bon développement !** 🚀

