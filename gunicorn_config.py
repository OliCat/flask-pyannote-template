"""
Configuration Gunicorn pour l'application Flask Pyannote

Usage:
    gunicorn -c gunicorn_config.py app:app
"""

import multiprocessing
import os

# Nombre de workers
# Pour MPS isolé: peut utiliser plusieurs workers (recommandé: 2-4)
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count()))

# Threads par worker
threads = 2

# Classe de worker
worker_class = 'sync'  # sync pour Python pur, gevent pour async

# Timeout
timeout = 600  # 10 minutes (pour les longs fichiers audio)

# Keepalive
keepalive = 5

# Nombre de connexions simultanées par worker
worker_connections = 1000

# Interface
bind = os.environ.get('BIND', '0.0.0.0:5000')

# Logging
accesslog = os.environ.get('ACCESS_LOG', '-')
errorlog = os.environ.get('ERROR_LOG', '-')
loglevel = os.environ.get('LOG_LEVEL', 'info')

# Process naming
proc_name = 'flask_pyannote'

# PID file
pidfile = os.environ.get('PID_FILE', None)

# User/Group (optionnel, pour production)
# user = 'www-data'
# group = 'www-data'

# Preload app (charge l'app avant le fork des workers)
# Utile pour partager la mémoire, mais peut causer des problèmes avec MPS
# Recommandé: False pour MPS isolé
preload_app = False

# Max requests (redémarrer worker après N requêtes, pour éviter les fuites mémoire)
max_requests = 1000
max_requests_jitter = 50

# Graceful timeout (temps pour terminer gracieusement)
graceful_timeout = 30

# Logging format
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

