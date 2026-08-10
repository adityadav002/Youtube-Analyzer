import os
from celery import Celery
from app import create_app

def make_celery(app_name=__name__):
    env = os.environ.get('FLASK_ENV', 'production')
    flask_app = create_app(env)
    
    celery = Celery(
        app_name,
        include=['app.jobs.channel_jobs', 'app.jobs.video_jobs']
    )
    
    if flask_app.config.get('USE_CELERY'):
        celery.conf.update(
            broker_url=flask_app.config.get('broker_url'),
            result_backend=flask_app.config.get('result_backend'),
        )
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

celery_app = make_celery()

