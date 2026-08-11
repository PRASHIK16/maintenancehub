web: daphne -b 0.0.0.0 -p $PORT config.asgi:application
worker: celery -A config.celery_app worker --loglevel=info
beat: celery -A config.celery_app beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
release: python manage.py migrate --noinput
