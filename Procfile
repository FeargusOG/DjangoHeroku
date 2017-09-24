web: gunicorn DjangoHerokuSite.wsgi
worker: celery -A DjangoHerokuSite worker --beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
