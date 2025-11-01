# Guide: Pyannote MPS avec Flask/Gunicorn

## 🎯 Problématique identifiée

**Flask/Gunicorn peut causer des crashs mémoire avec MPS**, même si MPS fonctionne bien dans une application standalone.

## 🔍 Pourquoi Flask/Gunicorn pose problème avec MPS ?

### Problèmes spécifiques

1. **Workers multiples**
   - Gunicorn lance plusieurs workers (processus ou threads)
   - Chaque worker peut essayer d'utiliser MPS
   - **Problème**: MPS ne partage pas bien les ressources entre processus
   - **Résultat**: Crashs OOM (Out Of Memory)

2. **Gestion mémoire des workers**
   - Les workers réutilisés peuvent garder la mémoire GPU
   - Pas de nettoyage automatique entre les requêtes
   - **Problème**: Accumulation de mémoire MPS
   - **Résultat**: Crashs progressifs

3. **Partage de contexte MPS**
   - MPS n'est pas thread-safe pour le partage de contexte
   - Workers threads partagent le même espace mémoire
   - **Problème**: Conflits d'accès GPU
   - **Résultat**: Crashs aléatoires

4. **Charge concurrente**
   - Plusieurs requêtes simultanées = plusieurs workers actifs
   - Chaque worker charge son propre modèle pyannote
   - **Problème**: Multiplication de l'utilisation mémoire
   - **Résultat**: Crashs sous charge

---

## ✅ Solutions pour Flask/Gunicorn

### Solution 1: Workers = 1 (Simple mais limité)

**Configuration Gunicorn:**
```bash
gunicorn --workers 1 --threads 4 app:app
```

**Avantages:**
- ✅ Évite les conflits MPS entre workers
- ✅ Simple à implémenter

**Inconvénients:**
- ⚠️ Pas de parallélisation vraie
- ⚠️ Limite la capacité concurrente

**Quand utiliser:**
- Tests et développement
- Charge faible
- Environnement de production limité

---

### Solution 2: CPU par défaut, MPS optionnel (Recommandé)

**Stratégie:**
- **Par défaut**: CPU (stable pour tous les workers)
- **MPS optionnel**: Uniquement si worker=1 et requête explicite

**Implémentation:**
```python
from pyannote_mps_helper import create_pyannote_pipeline_safe
import os

def get_pipeline(use_mps=False):
    """Crée un pipeline pyannote de manière sécurisée"""
    
    # Détection automatique: MPS seulement si worker unique
    gunicorn_workers = os.environ.get('GUNICORN_WORKERS', '1')
    
    if use_mps and int(gunicorn_workers) > 1:
        print("⚠️ MPS désactivé: Gunicorn a plusieurs workers")
        use_mps = False
    
    pipeline = create_pyannote_pipeline_safe(
        prefer_mps=use_mps,
        embedding_batch_size=16
    )
    
    return pipeline
```

**Configuration Gunicorn:**
```bash
# Pour CPU (recommandé)
gunicorn --workers 4 --threads 2 app:app

# Pour MPS (si vraiment nécessaire)
GUNICORN_WORKERS=1 gunicorn --workers 1 --threads 4 app:app
```

---

### Solution 3: Pool de pipelines préchargés (Avancé)

**Stratégie:**
- Précharger un pool de pipelines au démarrage
- Workers réutilisent les pipelines du pool
- Gestion mémoire centralisée

**Implémentation:**
```python
from queue import Queue
import threading

class PipelinePool:
    def __init__(self, pool_size=2, use_mps=False):
        self.pool = Queue(maxsize=pool_size)
        self.use_mps = use_mps and pool_size == 1  # MPS seulement si pool=1
        
        # Précharger les pipelines
        for _ in range(pool_size):
            pipeline = create_pyannote_pipeline_safe(
                prefer_mps=self.use_mps,
                embedding_batch_size=16
            )
            self.pool.put(pipeline)
    
    def get(self):
        return self.pool.get()
    
    def put(self, pipeline):
        # Nettoyer avant de remettre
        if self.use_mps:
            torch.mps.empty_cache()
        gc.collect()
        self.pool.put(pipeline)

# Pool global (initialisé au démarrage)
pipeline_pool = PipelinePool(pool_size=2, use_mps=False)

@app.route('/transcribe', methods=['POST'])
def transcribe():
    pipeline = pipeline_pool.get()
    try:
        result = pipeline(audio_file)
        return result
    finally:
        pipeline_pool.put(pipeline)
```

**Configuration:**
- **CPU**: `pool_size=2-4` (selon RAM)
- **MPS**: `pool_size=1` (un seul pipeline MPS)

---

### Solution 4: Worker spécialisé MPS (Architecture recommandée)

**Stratégie:**
- **Worker 1**: MPS (un seul worker dédié)
- **Workers 2-N**: CPU (workers normaux)
- Route les requêtes selon disponibilité

**Architecture:**
```
Gunicorn
├── Worker 1 (MPS) - Traite les requêtes prioritaires
├── Worker 2 (CPU) - Traite les requêtes normales
├── Worker 3 (CPU) - Traite les requêtes normales
└── Worker 4 (CPU) - Traite les requêtes normales
```

**Implémentation:**
```python
import os

def create_pipeline_for_worker():
    """Crée un pipeline selon le numéro de worker"""
    worker_id = os.environ.get('GUNICORN_WORKER_ID', '0')
    
    # Worker 1 utilise MPS, autres utilisent CPU
    use_mps = (worker_id == '1')
    
    return create_pyannote_pipeline_safe(
        prefer_mps=use_mps,
        embedding_batch_size=16 if use_mps else 32
    )

# Pipeline chargé une fois par worker
pipeline = create_pipeline_for_worker()
```

**Configuration Gunicorn:**
```bash
gunicorn --workers 4 --threads 2 \
  --worker-class sync \
  --env GUNICORN_WORKER_ID={{ worker_id }} \
  app:app
```

---

## 🛠️ Configuration recommandée pour votre projet Flask

### Pour la stabilité (Production)

```python
# config.py
import os

# Détection automatique de l'environnement
IS_GUNICORN = 'gunicorn' in os.environ.get('SERVER_SOFTWARE', '')
WORKER_COUNT = int(os.environ.get('GUNICORN_WORKERS', '1'))

# Configuration MPS
USE_MPS = False  # Par défaut désactivé pour Flask/Gunicorn
if IS_GUNICORN:
    # MPS seulement si un seul worker
    USE_MPS = USE_MPS and WORKER_COUNT == 1
    EMBEDDING_BATCH_SIZE = 16  # Conservateur pour éviter OOM
else:
    # Application standalone peut utiliser MPS
    USE_MPS = True
    EMBEDDING_BATCH_SIZE = 16

# Fonction helper
def get_pyannote_pipeline():
    from pyannote_mps_helper import create_pyannote_pipeline_safe
    
    return create_pyannote_pipeline_safe(
        prefer_mps=USE_MPS,
        embedding_batch_size=EMBEDDING_BATCH_SIZE
    )
```

### Dans votre route Flask

```python
from flask import Flask, request, jsonify
from config import get_pyannote_pipeline

app = Flask(__name__)

# Pipeline chargé une fois au démarrage du worker
pipeline = get_pyannote_pipeline()

@app.route('/api/diarize', methods=['POST'])
def diarize():
    audio_file = request.files['audio']
    
    try:
        # Traitement avec gestion mémoire
        from pyannote_mps_helper import process_with_memory_management
        import torch
        
        device = torch.device('mps' if 'mps' in str(pipeline.device) else 'cpu')
        result = process_with_memory_management(pipeline, audio_file, device)
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        # Fallback vers CPU si erreur
        pipeline.to(torch.device('cpu'))
        result = pipeline(audio_file)
        
        return jsonify({
            'success': True,
            'result': result,
            'fallback_cpu': True
        })
```

---

## 🔧 Configuration Gunicorn optimale

### Pour CPU (Recommandé pour production)

```bash
# gunicorn_config.py
workers = 4
threads = 2
worker_class = 'sync'
worker_connections = 1000
timeout = 300
keepalive = 5
```

```bash
gunicorn -c gunicorn_config.py app:app
```

### Pour MPS (Test seulement)

```bash
# MPS nécessite un seul worker
gunicorn --workers 1 --threads 4 --timeout 600 app:app
```

**⚠️ Limitation**: Un seul worker = pas de parallélisation vraie

---

## 📊 Comparaison des approches

| Approche | Workers | MPS | Stabilité | Performance | Production |
|----------|---------|-----|-----------|-------------|------------|
| **1 Worker** | 1 | ✅ | ⚠️ | ⚡ | ❌ |
| **CPU par défaut** | 4+ | ❌ | ✅ | 🐢 | ✅ |
| **Pool pipelines** | 2-4 | ⚠️ | ✅ | ⚡ | ✅ |
| **Worker MPS dédié** | 4 (1 MPS) | ✅ | ✅ | ⚡⚡ | ✅ |

---

## 💡 Recommandation finale

### Pour votre projet Flask/Gunicorn :

1. **Production**: CPU par défaut, workers multiples
   ```python
   USE_MPS = False  # Stable pour tous les workers
   WORKERS = 4      # Bonne parallélisation
   ```

2. **Développement/Test**: MPS optionnel avec worker unique
   ```python
   USE_MPS = True   # Test seulement
   WORKERS = 1      # Évite les conflits
   ```

3. **Hybride**: Worker dédié MPS + workers CPU
   - Meilleur compromis performance/stabilité
   - Plus complexe à mettre en place

---

## 🚨 Points d'attention

1. **Nettoyage mémoire obligatoire**
   - Appeler `torch.mps.empty_cache()` entre requêtes
   - Utiliser `process_with_memory_management()` du helper

2. **Pas de partage de pipeline entre workers**
   - Chaque worker doit avoir son propre pipeline
   - Pas de variable globale partagée

3. **Gestion des erreurs OOM**
   - Toujours prévoir un fallback CPU
   - Logger les erreurs pour debugging

4. **Monitoring**
   - Surveiller la mémoire GPU dans Activity Monitor
   - Logger les temps de traitement
   - Alerter si trop d'OOM

---

## ✅ Checklist d'implémentation

- [ ] Utiliser `pyannote_mps_helper.py` (déjà créé)
- [ ] Désactiver MPS par défaut si `workers > 1`
- [ ] Implémenter fallback CPU automatique
- [ ] Nettoyer la mémoire entre requêtes
- [ ] Tester avec un worker (MPS)
- [ ] Tester avec plusieurs workers (CPU)
- [ ] Monitorer la mémoire en production
- [ ] Documenter la configuration

---

**Conclusion**: Flask/Gunicorn avec plusieurs workers ne fonctionne pas bien avec MPS. Utilisez CPU par défaut en production, MPS uniquement pour tests avec un seul worker.

