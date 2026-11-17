import os
import json
import logging
import re
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
    _cached_model: Optional[str] = None
    _cached_api_version: str = "v1beta"

    @classmethod
    def get_model_name(cls) -> str:
        return os.environ.get('AI_MODEL') or cls._cached_model or 'gemini-3.8-flash'

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

    @classmethod
    def _execute_gemini_request(cls, api_key: str, payload: dict, video_id: str) -> dict:
        """
        Executes generateContent against Gemini API with automatic model & version fallback.
        If the primary model returns 404 ("not found for API version ..."), it tries fallbacks
        and queries ListModels to discover the active models supported by the API key.
        """
        default_candidates = [
            'gemini-3.8-flash',
            'gemini-flash-latest',
            'gemini-3.5-flash',
            'gemini-3-flash-preview',
            'gemini-3.8-flash-lite',
            'gemini-3.5-flash-lite',
            'gemini-2.5-flash',
            'gemini-2.0-flash',
            'gemini-1.5-flash',
            'gemini-pro-latest',
            'gemini-2.5-pro'
        ]

        env_model = os.environ.get('AI_MODEL')
        if env_model:
            candidates = [env_model] + [c for c in default_candidates if c != env_model]
        else:
            candidates = [cls._cached_model] if cls._cached_model else []
            candidates.extend([c for c in default_candidates if c not in candidates])

        api_versions = ['v1beta', 'v1']
        last_error = None

        for model in candidates:
            for api_ver in api_versions:
                url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{model}:generateContent?key={api_key}"
                try:
                    resp = requests.post(url, json=payload, timeout=60)
                except requests.exceptions.Timeout as te:
                    logger.warning(f"[AIAnalysisService] Model '{model}' on '{api_ver}' timed out after 60s for video {video_id}. Trying fallback...")
                    last_error = f"Model '{model}' timed out"
                    continue
                except requests.exceptions.RequestException as re:
                    logger.warning(f"[AIAnalysisService] Network error calling model '{model}' on '{api_ver}': {re}. Trying fallback...")
                    last_error = str(re)
                    continue

                if resp.status_code == 200:
                    cls._cached_model = model
                    cls._cached_api_version = api_ver
                    logger.info(f"[AIAnalysisService] Successfully used model '{model}' on '{api_ver}'")
                    return resp.json()

                err_text = resp.text
                try:
                    err_json = resp.json()
                    err_msg = err_json.get('error', {}).get('message', err_text)
                except Exception:
                    err_msg = err_text

                # If 404 (model not found for this API version), try next candidate
                if resp.status_code == 404 or "not found for api version" in err_msg.lower():
                    logger.warning(f"[AIAnalysisService] Model '{model}' on '{api_ver}' returned 404: {err_msg}. Trying fallback...")
                    last_error = err_msg
                    continue

                if resp.status_code == 429:
                    raise AIAnalysisError("Gemini AI quota exceeded or rate limited.", status_code=429)
                elif resp.status_code == 400:
                    if "not supported for generatecontent" in err_msg.lower():
                        last_error = err_msg
                        continue
                    # Check if responseMimeType is rejected, retry without it
                    if "responsemimetype" in err_msg.lower() or "generationconfig" in err_msg.lower():
                        logger.warning(f"[AIAnalysisService] Model '{model}' failed with generationConfig ({err_msg}). Retrying without responseMimeType...")
                        fallback_payload = {"contents": payload.get("contents", [])}
                        try:
                            retry_resp = requests.post(url, json=fallback_payload, timeout=60)
                            if retry_resp.status_code == 200:
                                cls._cached_model = model
                                cls._cached_api_version = api_ver
                                logger.info(f"[AIAnalysisService] Successfully used model '{model}' without responseMimeType on '{api_ver}'")
                                return retry_resp.json()
                        except Exception as retry_err:
                            logger.warning(f"[AIAnalysisService] Fallback request without responseMimeType failed: {retry_err}")

                    raise AIAnalysisError(f"Invalid Gemini API request: {err_msg}", status_code=400)

                last_error = err_msg

        # If candidates failed, query ListModels to find authorized models for this key
        logger.info("[AIAnalysisService] Candidate models failed. Querying ListModels to auto-discover models for this API key...")
        discovered_models = []
        for api_ver in ('v1beta', 'v1'):
            try:
                list_resp = requests.get(f"https://generativelanguage.googleapis.com/{api_ver}/models?key={api_key}", timeout=15)
                if list_resp.status_code == 200:
                    models_data = list_resp.json().get('models', [])
                    supported = [
                        m.get('name', '').replace('models/', '')
                        for m in models_data
                        if 'generateContent' in m.get('supportedGenerationMethods', [])
                    ]
                    if supported:
                        excluded_keywords = ['-tts', '-image', '-customtools', 'lyria-', 'nano-', 'robotics', 'transcribe']
                        filtered = [m for m in supported if not any(k in m for k in excluded_keywords)]

                        def model_priority(name: str) -> int:
                            if name == 'gemini-3.8-flash':
                                return 0
                            if 'gemini' in name and 'flash' in name:
                                return 1
                            if 'gemini' in name and 'pro' in name:
                                return 2
                            if 'gemini' in name:
                                return 3
                            if 'gemma' in name:
                                return 4
                            return 5

                        sorted_models = sorted(filtered or supported, key=model_priority)
                        logger.info(f"[AIAnalysisService] Prioritized models on {api_ver}: {sorted_models}")

                        for discovered_model in sorted_models:
                            retry_url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{discovered_model}:generateContent?key={api_key}"
                            try:
                                retry_resp = requests.post(retry_url, json=payload, timeout=60)
                                if retry_resp.status_code == 200:
                                    cls._cached_model = discovered_model
                                    cls._cached_api_version = api_ver
                                    logger.info(f"[AIAnalysisService] Auto-discovery succeeded with model '{discovered_model}' on '{api_ver}'")
                                    return retry_resp.json()

                                logger.warning(
                                    f"[AIAnalysisService] Auto-discovery candidate '{discovered_model}' on {api_ver} failed: status {retry_resp.status_code}, error: {retry_resp.text[:200]}"
                                )
                                # If 400 or responseMimeType issue, retry without generationConfig
                                if retry_resp.status_code == 400:
                                    fallback_payload = {"contents": payload.get("contents", [])}
                                    retry_resp2 = requests.post(retry_url, json=fallback_payload, timeout=60)
                                    if retry_resp2.status_code == 200:
                                        cls._cached_model = discovered_model
                                        cls._cached_api_version = api_ver
                                        logger.info(f"[AIAnalysisService] Auto-discovery succeeded without responseMimeType for model '{discovered_model}'")
                                        return retry_resp2.json()
                            except Exception as re_err:
                                logger.warning(f"[AIAnalysisService] Candidate '{discovered_model}' encountered error: {re_err}")

                        discovered_models.extend(sorted_models)
            except Exception as e:
                logger.warning(f"[AIAnalysisService] Failed querying ListModels on {api_ver}: {e}")

        if discovered_models:
            raise AIAnalysisError(
                f"Configured model failed. Available models for your API key: {', '.join(discovered_models[:10])}. "
                f"Set AI_MODEL in your environment variables to one of these.",
                status_code=404
            )
        elif last_error and "timed out" in last_error.lower():
            raise AIAnalysisError("Gemini AI request timed out. Please try again later.", status_code=504)
        else:
            raise AIAnalysisError(
                f"Gemini AI error: {last_error or 'No available Gemini models found for this API key'}. "
                "Please verify your GEMINI_API_KEY has the Generative Language API enabled in Google AI Studio / Google Cloud.",
                status_code=404
            )

    @staticmethod
    def _parse_gemini_json_response(data: dict, video_id: str) -> dict:
        """
        Safely extracts and parses JSON from Gemini/Gemma responses,
        stripping markdown code fences (```json ... ```) or extracting
        outermost JSON blocks via regex.
        """
        candidates = data.get('candidates', [])
        if not candidates:
            raise AIAnalysisError("No candidates returned from Gemini API.", status_code=502)

        parts = candidates[0].get('content', {}).get('parts', [])
        text_parts = [p.get('text', '') for p in parts if isinstance(p, dict) and p.get('text')]
        raw_text = "\n".join(text_parts).strip()

        if not raw_text:
            raise AIAnalysisError("Empty response text received from Gemini API.", status_code=502)

        cleaned = raw_text.strip()
        # Strip markdown fences if present
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except Exception:
            # Fallback: extract JSON object via regex
            match = re.search(r'\{[\s\S]*\}', raw_text)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception as sub_err:
                    logger.error(f"Regex JSON parse failed for video {video_id}: {sub_err}. Raw text: {raw_text[:300]}")
            logger.error(f"Failed to parse Gemini response for video {video_id}. Raw text: {raw_text[:300]}")
            raise AIAnalysisError("Failed to parse AI analysis response from Gemini.", status_code=502)

    @staticmethod
    def analyze_video(video_id: str, analysis_type: str = 'full') -> Dict[str, Any]:
        """
        Executes AI analysis for a video using Google Gemini.
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

        data = AIAnalysisService._execute_gemini_request(api_key, payload, video_id)
        result_json = AIAnalysisService._parse_gemini_json_response(data, video_id)

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

