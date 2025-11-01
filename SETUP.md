# Guide d'installation détaillé

## 📋 Prérequis

- Python 3.8 ou supérieur
- ffmpeg (pour la conversion audio)
- Compte HuggingFace avec token d'accès

## 🔧 Installation complète

### 1. Cloner ou copier le template

```bash
# Si depuis GitHub
git clone https://github.com/votre-username/flask-pyannote-template.git
cd flask-pyannote-template

# OU copier manuellement le dossier
```

### 2. Créer l'environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# ou
venv\Scripts\activate     # Windows
```

### 3. Installer les dépendances

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Installer ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Télécharger depuis https://ffmpeg.org/

### 5. Configurer HuggingFace

```bash
# Installer huggingface-cli si nécessaire
pip install huggingface_hub

# Se connecter avec votre token
huggingface-cli login
```

**Token HuggingFace:**
1. Créer un compte sur [HuggingFace](https://huggingface.co/)
2. Générer un token dans [Settings > Access Tokens](https://huggingface.co/settings/tokens)
3. Accepter les conditions pour:
   - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)

### 6. Modules nécessaires ✅

**Les modules suivants sont déjà inclus dans le template:**
- ✅ `pyannote_isolated.py` - Module d'isolation MPS
- ✅ `pyannote_mps_helper.py` - Helper MPS sécurisé

Ces fichiers sont dans le même répertoire que `app.py` et sont prêts à l'emploi.

### 7. Configuration optionnelle

```bash
# Copier l'exemple de configuration
cp .env.example .env

# Éditer selon vos besoins
nano .env
```

## ✅ Vérification de l'installation

### Tester que tout fonctionne

```bash
# Mode développement
python app.py
```

Ouvrir http://localhost:5000/health dans un navigateur.

Vous devriez voir:
```json
{
  "status": "ok",
  "mps_available": true,
  ...
}
```

### Tester l'API

```bash
# Health check
curl http://localhost:5000/health

# Test avec un fichier audio
curl -X POST \
  -F "audio=@test.wav" \
  http://localhost:5000/api/v1/diarize
```

## 🚀 Démarrage en production

```bash
# Avec Gunicorn
gunicorn -c gunicorn_config.py app:app

# Avec variables d'environnement
GUNICORN_WORKERS=4 gunicorn -c gunicorn_config.py app:app
```

## 🐛 Problèmes courants

### ImportError: No module named 'pyannote_isolated'

**Solution:** Copier `pyannote_isolated.py` dans le même répertoire que `app.py`.

### ImportError: No module named 'pyannote_mps_helper'

**Solution:** Copier `pyannote_mps_helper.py` dans le même répertoire que `app.py`.

### ffmpeg: command not found

**Solution:** Installer ffmpeg (voir étape 4).

### Authentication required (HuggingFace)

**Solution:** 
1. Vérifier que vous êtes connecté: `huggingface-cli whoami`
2. Vérifier que vous avez accepté les conditions d'utilisation des modèles
3. Vérifier que votre token a les bonnes permissions

### OOM (Out of Memory) sur MPS

**Solution:**
- Réduire `batch_size` (essayer 8 ou 4)
- Le fallback CPU se déclenche automatiquement
- Consulter [MPS_ISOLATION_GUIDE.md](../MPS_ISOLATION_GUIDE.md) pour plus de détails

## 📚 Documentation complète

- [README.md](README.md) - Documentation principale
- [TEMPLATE_README.md](TEMPLATE_README.md) - Guide du template
- [MPS_ISOLATION_GUIDE.md](MPS_ISOLATION_GUIDE.md) - Guide détaillé sur l'isolation MPS
- [FLASK_GUNICORN_MPS_GUIDE.md](FLASK_GUNICORN_MPS_GUIDE.md) - Guide Flask/Gunicorn avec MPS
- [CONTRIBUTING.md](CONTRIBUTING.md) - Guide de contribution

## ✅ Installation réussie ?

Si tout fonctionne, vous êtes prêt à utiliser le template ! 🎉

