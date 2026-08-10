from flask import Blueprint, jsonify, request, current_app
from app.models.queue import ProcessingQueue
from app.models.video import Video
from app.models.channel import Channel
from app import db
from app.utils.task_dispatcher import dispatch_task
import uuid

jobs_bp = Blueprint('jobs', __name__, url_prefix='/api/jobs')

@jobs_bp.route('', methods=['GET'])
def get_jobs():
    try:
        status_filter = request.args.get('status')
        type_filter = request.args.get('job_type')
        
        query = db.session.query(ProcessingQueue)
        
        if status_filter and status_filter != 'all':
            query = query.filter(ProcessingQueue.status == status_filter)
        if type_filter and type_filter != 'all':
            query = query.filter(ProcessingQueue.job_type == type_filter)
            
        jobs = query.order_by(ProcessingQueue.created_at.desc()).all()
        
        results = []
        for job in jobs:
            target_title = None
            if job.job_type in ['extract_video', 'download_video']:
                video = db.session.query(Video).filter(Video.id == job.target_id).first()
                if video:
                    target_title = video.title
            elif job.job_type in ['crawl_channel', 'extract_channel']:
                channel = db.session.query(Channel).filter(Channel.id == job.target_id).first()
                if channel:
                    target_title = channel.display_name
                    
            if not target_title:
                target_title = job.payload.get('video_title') or job.payload.get('channel_title') or f"Target: {job.target_id}"

            results.append({
                'id': job.id,
                'job_type': job.job_type,
                'target_id': job.target_id,
                'target_title': target_title,
                'status': job.status,
                'priority': job.priority,
                'retry_count': job.retry_count,
                'error_message': job.error_message,
                'payload': job.payload,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'updated_at': job.updated_at.isoformat() if job.updated_at else None,
            })
            
        return jsonify(results), 200
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Failed to query background jobs")
        return jsonify({'error': 'Failed to retrieve background jobs'}), 500

@jobs_bp.route('/<job_id>', methods=['GET'])
def get_job_status(job_id):
    job = db.session.query(ProcessingQueue).get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
        
    return jsonify({
        'id': job.id,
        'status': job.status,
        'target_id': job.target_id,
        'job_type': job.job_type,
        'error_message': job.error_message,
        'payload': job.payload,
        'created_at': job.created_at.isoformat() if job.created_at else None,
        'updated_at': job.updated_at.isoformat() if job.updated_at else None,
    })

@jobs_bp.route('/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    job = db.session.query(ProcessingQueue).get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
        
    if job.status not in ['queued', 'processing']:
        return jsonify({'error': f"Cannot cancel a job with status '{job.status}'"}), 400
        
    try:
        job.status = 'cancelled'
        
        if current_app.config.get('USE_CELERY'):
            try:
                from app.jobs.celery_app import celery_app
                celery_app.control.revoke(job.id, terminate=True)
            except Exception as ce:
                import logging
                logging.getLogger(__name__).warning(f"Failed to revoke celery task {job.id}: {str(ce)}")
                
        db.session.commit()
        return jsonify({'status': 'cancelled'}), 200
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).exception("Failed to cancel job")
        return jsonify({'error': 'Failed to cancel job'}), 500

@jobs_bp.route('/<job_id>/retry', methods=['POST'])
def retry_job(job_id):
    job = db.session.query(ProcessingQueue).get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
        
    if job.status not in ['failed', 'cancelled']:
        return jsonify({'error': f"Cannot retry a job with status '{job.status}'"}), 400
        
    try:
        new_job_id = str(uuid.uuid4())
        
        new_job = ProcessingQueue(
            id=new_job_id,
            job_type=job.job_type,
            target_id=job.target_id,
            status='queued',
            priority=job.priority,
            retry_count=job.retry_count + 1,
            payload=job.payload
        )
        db.session.add(new_job)
        
        if job.job_type == 'download_video':
            history_id = job.payload.get('history_id')
            if history_id:
                from app.models.history import DownloadHistory
                history = db.session.query(DownloadHistory).get(history_id)
                if history:
                    history.status = 'pending'
                    history.progress_percent = 0
                    history.error_message = None
        
        db.session.commit()
        
        if job.job_type == 'crawl_channel':
            from app.jobs.video_jobs import crawl_channel_videos_task
            dispatch_task(crawl_channel_videos_task, new_job_id, job.target_id)
        elif job.job_type == 'extract_video':
            from app.jobs.video_jobs import extract_video_metadata_task
            dispatch_task(extract_video_metadata_task, new_job_id, job.target_id)
        elif job.job_type == 'extract_channel':
            from app.jobs.channel_jobs import extract_channel_metadata_task
            dispatch_task(extract_channel_metadata_task, new_job_id, job.target_id)
        elif job.job_type == 'download_video':
            from app.jobs.video_jobs import download_video_task
            history_id = job.payload.get('history_id')
            dispatch_task(download_video_task, new_job_id, history_id)
            
        return jsonify({
            'job_id': new_job_id,
            'status': 'queued'
        }), 202
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).exception("Failed to retry job")
        return jsonify({'error': 'Failed to retry job'}), 500


