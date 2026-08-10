import threading
from flask import current_app

def dispatch_task(task, *args, **kwargs):
    """
    Conditionally dispatches a task.
    If USE_CELERY is True, it sends the task to the Celery worker queue via .delay().
    If USE_CELERY is False, it executes the task asynchronously in a background thread.
    """
    try:
        app = current_app._get_current_object()
        use_celery = app.config.get('USE_CELERY', False)
    except RuntimeError:
        use_celery = True
        app = None

    if use_celery:
        return task.delay(*args, **kwargs)
    else:
        def run_in_context():
            with app.app_context():
                try:
                    task(*args, **kwargs)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).exception("Error in background thread task")
                    
        thread = threading.Thread(target=run_in_context)
        thread.daemon = True
        thread.start()
        return thread
