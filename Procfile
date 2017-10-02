web: gunicorn DjangoHerokuSite.wsgi --log-level warning
worker: celery -A DjangoHerokuSite worker --beat -l warning --scheduler django_celery_beat.schedulers:DatabaseScheduler
