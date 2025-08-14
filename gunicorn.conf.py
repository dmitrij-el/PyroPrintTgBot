# gunicorn.conf.py
import multiprocessing

bind = "0.0.0.0:49556"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
loglevel = "info"
preload_app = True
accesslog = "-"
errorlog = "-"