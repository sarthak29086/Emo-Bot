"""
routes_emotion.py
-----------------
FastAPI routes for face emotion detection, voice emotion detection,
and multimodal fusion.

Fixes (v2.1):
  - Added `no_face_detected` field to FaceEmotionResponse
  - Voice response returns real softmax confidence
  - Added URL aliases for frontend compatibility:
    POST /api/detect_face_emotion (legacy alias)
    POST /api/detect_voice_emotion (legacy alias)
    POST /api/fuse_emotions (analytics dashboard alias)
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from emotion_detection.face_emotion import FaceEmotionDetector, EmotionResult
from emotion_detection.fusion import fuse_emotions
from dependencies import face_detector, voice_detector
from api.ros_publisher import publish_emotion_to_ros

router = APIRouter(prefix="/api", tags=["Emotion Detection"])

# Use the shared singletons
_detector_face = face_detector
_detector_voice = voice_detector


# ── Request / Response schemas ─────────────────────────────────────────────

class FaceEmotionRequest(BaseModel):
    image_base64: str           # data:image/jpeg;base64,...


class FaceEmotionResponse(BaseModel):
    dominant_emotion:   str
    confidence:         float
    all_emotions:       dict[str, float]
    landmarks_detected: bool
    processing_time_ms: float
    smoothed:           bool
    no_face_detected:   bool = False


class VoiceEmotionRequest(BaseModel):
    audio_base64: str           # base64 audio data (webm, wav, or ogg)


class TopPrediction(BaseModel):
    emotion: str
    confidence: float


class VoiceEmotionResponse(BaseModel):
    emotion: str
    confidence: float
    top_predictions: Optional[List[TopPrediction]] = []


class FusionRequest(BaseModel):
    face_emotion: str
    face_confidence: float
    voice_emotion: str
    voice_confidence: float


class FusionResponse(BaseModel):
    fused_emotion: str
    face_weight: float
    voice_weight: float
    ros_behavior: dict


# ── Face Detection ─────────────────────────────────────────────────────────

def _face_detect_logic(image_base64: str) -> FaceEmotionResponse:
    """Shared logic for all face detection endpoint variants."""
    if not image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")

    result: EmotionResult = _detector_face.detect_from_base64(image_base64)
    return FaceEmotionResponse(
        dominant_emotion   = result.dominant_emotion,
        confidence         = result.confidence,
        all_emotions       = result.all_emotions,
        landmarks_detected = result.landmarks_detected,
        processing_time_ms = result.processing_time_ms,
        smoothed           = result.smoothed,
        no_face_detected   = result.no_face_detected,
    )


# Primary route
@router.post("/detect/face", response_model=FaceEmotionResponse)
async def detect_face_emotion(body: FaceEmotionRequest, background_tasks: BackgroundTasks):
    result = _face_detect_logic(body.image_base64)
    # Fire ROS2 speech publish if a real emotion is detected (non-neutral, face present)
    if not result.no_face_detected and result.dominant_emotion != "neutral":
        background_tasks.add_task(publish_emotion_to_ros, result.dominant_emotion)
    return result


# Legacy alias (used by some older frontend code)
@router.post("/detect_face_emotion", response_model=FaceEmotionResponse, include_in_schema=False)
async def detect_face_emotion_alias(body: FaceEmotionRequest):
    return _face_detect_logic(body.image_base64)


# ── Voice Detection ────────────────────────────────────────────────────────

def _voice_detect_logic(audio_base64: str) -> VoiceEmotionResponse:
    """Shared logic for all voice detection endpoint variants."""
    if not audio_base64:
        raise HTTPException(status_code=400, detail="audio_base64 is required")

    try:
        import base64
        # Strip data-URI prefix if present (e.g. "data:audio/webm;base64,")
        raw_b64 = audio_base64.split(",")[-1]
        audio_data = base64.b64decode(raw_b64)

        result = _detector_voice.predict_emotion(audio_data)

        top_preds = [
            TopPrediction(emotion=p["emotion"], confidence=p["confidence"])
            for p in result.get("top_predictions", [])
        ]

        return VoiceEmotionResponse(
            emotion=result["emotion"],
            confidence=result["confidence"],
            top_predictions=top_preds,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice detection failed: {str(e)}")


# Primary route
@router.post("/detect/voice", response_model=VoiceEmotionResponse)
async def detect_voice_emotion(body: VoiceEmotionRequest):
    return _voice_detect_logic(body.audio_base64)


# Legacy alias
@router.post("/detect_voice_emotion", response_model=VoiceEmotionResponse, include_in_schema=False)
async def detect_voice_emotion_alias(body: VoiceEmotionRequest):
    return _voice_detect_logic(body.audio_base64)


# ── Multimodal Fusion ──────────────────────────────────────────────────────

def _fuse_logic(
    face_emotion: str,
    face_confidence: float,
    voice_emotion: str,
    voice_confidence: float,
) -> FusionResponse:
    """Shared fusion logic for all route variants."""
    result = fuse_emotions(face_emotion, face_confidence, voice_emotion, voice_confidence)
    return FusionResponse(
        fused_emotion=result["fused_emotion"],
        ros_behavior=result["ros_behavior"],
    )


# Primary route
@router.post("/fuse", response_model=FusionResponse)
async def multimodal_fusion(body: FusionRequest, background_tasks: BackgroundTasks):
    """Weighted combination of face and voice emotions."""
    result = _fuse_logic(
        body.face_emotion, body.face_confidence,
        body.voice_emotion, body.voice_confidence,
    )
    # Fire ROS2 speech publish in background (non-blocking, 20s cooldown, skips neutral)
    background_tasks.add_task(publish_emotion_to_ros, result.fused_emotion)
    return result


# Alias — used by AnalyticsDashboard.tsx (was calling wrong URL)
@router.post("/fuse_emotions", response_model=FusionResponse, include_in_schema=False)
async def multimodal_fusion_alias(body: FusionRequest):
    return _fuse_logic(
        body.face_emotion, body.face_confidence,
        body.voice_emotion, body.voice_confidence,
    )