#!/bin/bash
# Script d'installation du template Flask Pyannote

set -e

echo "🚀 Installation du template Flask Pyannote"
echo "=========================================="
echo ""

# Vérifier que Python est disponible
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    exit 1
fi

# Créer l'environnement virtuel si nécessaire
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer l'environnement virtuel
echo "✅ Activation de l'environnement virtuel..."
source venv/bin/activate

# Installer les dépendances
echo "📥 Installation des dépendances Python..."
pip install --upgrade pip
pip install -r requirements.txt

# Vérifier si les modules pyannote sont présents
if [ ! -f "../pyannote_isolated.py" ]; then
    echo "⚠️  Module pyannote_isolated.py non trouvé dans le répertoire parent"
    echo "   Copiez-le depuis le répertoire principal du projet"
    echo "   cp ../pyannote_isolated.py ."
fi

if [ ! -f "../pyannote_mps_helper.py" ]; then
    echo "⚠️  Module pyannote_mps_helper.py non trouvé dans le répertoire parent"
    echo "   Copiez-le depuis le répertoire principal du projet"
    echo "   cp ../pyannote_mps_helper.py ."
fi

# Vérifier ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  ffmpeg n'est pas installé"
    echo "   Installation requise pour la conversion audio"
    echo "   macOS: brew install ffmpeg"
    echo "   Linux: sudo apt install ffmpeg"
fi

echo ""
echo "✅ Installation terminée !"
echo ""
echo "📋 Prochaines étapes:"
echo "   1. Configurer HuggingFace: huggingface-cli login"
echo "   2. Copier les modules:"
echo "      cp ../pyannote_isolated.py ."
echo "      cp ../pyannote_mps_helper.py ."
echo "   3. Lancer l'application:"
echo "      python app.py              # Mode dev"
echo "      gunicorn -c gunicorn_config.py app:app  # Mode prod"
echo ""

