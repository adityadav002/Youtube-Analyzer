import os
import json
import logging
import requests
from typing import Optional, Dict, Any

from app import db
from app.models.ai import AIAnalysis
from app.models.video import Video
from app.models.transcript import Transcript
from app.models.comment import Comment

logger = logging.getLogger(__name__)

class AIAnalysisError(Exception):
    def __init__(self, message, status_code=500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class AIAnalysisService:
    @staticmethod
    def get_api_key() -> Optional[str]:
        return os.environ.get('GEMINI_API_KEY') or os.environ.get('AI_API_KEY')

    @staticmethod
    def is_enabled() -> bool:
        provider = os.environ.get('AI_PROVIDER', 'gemini').lower()
        if provider == 'disabled':
            return False
        return bool(AIAnalysisService.get_api_key())

    @staticmethod
    def get_analysis(video_id: str, analysis_type: str = 'full') -> Optional[Dict[str, Any]]:
        record = db.session.query(AIAnalysis).filter(
            AIAnalysis.video_id == video_id,
            AIAnalysis.analysis_type == analysis_type
        ).order_by(AIAnalysis.created_at.desc()).first()
        
        if record:
            return {
                'id': record.id,
                'video_id': record.video_id,
                'analysis_type': record.analysis_type,
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'result': record.result
            }
        return None

    @staticmethod
    def analyze_video(video_id: str, analysis_type: str = 'full') -> Dict[str, Any]:
        """
        Executes AI analysis for a video using Google Gemini 1.5 Flash.
        """
        api_key = AIAnalysisService.get_api_key()
        if not api_key:
            raise AIAnalysisError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY or AI_API_KEY in your environment.",
                status_code=503
            )

        video = db.session.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise AIAnalysisError(f"Video '{video_id}' not found.", status_code=404)

        # 1. Gather context
        transcript = db.session.query(Transcript).filter(Transcript.video_id == video_id).first()
        comments = db.session.query(Comment).filter(Comment.video_id == video_id).limit(30).all()

        transcript_text = transcript.full_text[:12000] if transcript else ""
        comments_text = "\n".join([f"- {c.text}" for c in comments[:20]]) if comments else ""

        context_parts = [
            f"Title: {video.title}",
            f"Description: {video.description or 'None'}"
        ]
        if transcript_text:
            context_parts.append(f"Transcript Excerpt: {transcript_text}")
        if comments_text:
            context_parts.append(f"Sample Viewer Comments:\n{comments_text}")

        context_string = "\n\n".join(context_parts)

        # 2. Build prompt
        system_instruction = (
            "You are an expert video content analyzer. Analyze the provided YouTube video data. "
            "You must respond with valid JSON matching this schema:\n"
            "{\n"
            '  "summary": "Concise 2-3 paragraph summary of the video content and key points.",\n'
            '  "topics": [\n'
            '    {"topic": "Name of topic", "description": "1 sentence explanation"}\n'
            "  ],\n"
            '  "key_takeaways": ["Point 1", "Point 2", "Point 3"],\n'
            '  "sentiment": {\n'
            '    "overall": "positive|neutral|negative",\n'
            '    "score": 0.85,\n'
            '    "summary": "Brief explanation of audience reception and sentiment",\n'
            '    "positive_pct": 75,\n'
            '    "neutral_pct": 15,\n'
            '    "negative_pct": 10\n'
            "  }\n"
            "}"
        )

        user_prompt = f"{system_instruction}\n\nVideo Data:\n{context_string}"

        # 3. Call Google Gemini API
        model = os.environ.get('AI_MODEL', 'gemini-1.5-flash')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": user_prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=30)
        except requests.exceptions.Timeout as te:
            logger.error(f"Gemini API timed out for video {video_id}: {te}")
            raise AIAnalysisError("Gemini AI request timed out. Please try again later.", status_code=504) from te
        except requests.exceptions.RequestException as re:
            logger.error(f"Network error calling Gemini API for video {video_id}: {re}")
            raise AIAnalysisError("Failed to connect to Gemini AI API due to network error.", status_code=502) from re

        if resp.status_code != 200:
            err_msg = resp.text
            try:
                err_data = resp.json()
                err_msg = err_data.get('error', {}).get('message', resp.text)
            except Exception:
                pass
            logger.error(f"Gemini API returned HTTP {resp.status_code}: {err_msg}")
            if resp.status_code == 429:
                raise AIAnalysisError("Gemini AI quota exceeded or rate limited.", status_code=429)
            elif resp.status_code == 400:
                raise AIAnalysisError(f"Invalid Gemini API request: {err_msg}", status_code=400)
            raise AIAnalysisError(f"Gemini AI error: {err_msg}", status_code=resp.status_code)

        try:
            data = resp.json()
            candidates = data.get('candidates', [])
            if not candidates:
                raise ValueError("No candidates returned from Gemini.")
            text_response = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '{}')
            result_json = json.loads(text_response)
        except Exception as pe:
            logger.error(f"Failed to parse Gemini response for video {video_id}: {pe}")
            raise AIAnalysisError("Failed to parse AI analysis response from Gemini.", status_code=502) from pe

        # 4. Save to database
        record = db.session.query(AIAnalysis).filter(
            AIAnalysis.video_id == video_id,
            AIAnalysis.analysis_type == analysis_type
        ).first()

        if record:
            record.result = result_json
            record.prompt_used = user_prompt[:1000]
        else:
            record = AIAnalysis(
                video_id=video_id,
                analysis_type=analysis_type,
                prompt_used=user_prompt[:1000]
            )
            record.result = result_json
            db.session.add(record)

        db.session.commit()

        return {
            'id': record.id,
            'video_id': record.video_id,
            'analysis_type': record.analysis_type,
            'created_at': record.created_at.isoformat() if record.created_at else None,
            'result': record.result
        }

