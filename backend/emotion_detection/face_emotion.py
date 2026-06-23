"""
face_emotion.py — v3.1 (Bug Fix Release)
-----------------------------------------
FER + MTCNN for robust real-time face emotion detection.
  - MTCNN deep learning face detector (low light, angles, distance)  ← FIXED: was mtcnn=False
  - Sensitivity boosting for rare emotions (Anger, Surprise, Disgust)
  - 2-frame rolling smoother for instant reaction
  - Pre-warming on startup

Fixes applied (v3.0 → v3.1):
  1. MTCNN now actually enabled  (mtcnn=True)
  2. _run_fer returns boosted all_emotions (not raw)
  3. base64 decode now strips whitespace before decoding
  4. Removed dead scale/downscale code
  5. DeepFace wrapped with timeout guard
  6. Emotion keys unified with fusion module ("fear", "surprise")

Backend: FastAPI | Member 1 — AI & Memory Engineer
"""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from statistics import mode
from typing import Optional

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from deepface import DeepFace
try:
    from fer import FER  # fer<=22.x
except ImportError:
    from fer.fer import FER  # fer>=25.x

from .fer_cnn import FERCustomCNN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

EMOTIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
FER_IMG_SIZE = 48
SMOOTHER_WINDOW = 2  # Ultra-fast reaction

_DEFAULT_WEIGHTS = Path(__file__).parent / "fer_cnn.pth"

# Sensitivity multipliers — boost under-detected emotions
EMOTION_MULTIPLIERS = {
    "angry": 1.5,
    "surprise": 1.5,
    "disgust": 1.3,
    "fear": 1.2,
}

# Timeout (seconds) for DeepFace cold-start model download guard
_DEEPFACE_TIMEOUT = 10


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class FaceRegion:
    x: int
    y: int
    w: int
    h: int
    confidence: float


@dataclass
class EmotionResult:
    dominant_emotion: str
    confidence: float
    all_emotions: dict[str, float]
    face_region: Optional[FaceRegion]
    landmarks_detected: bool
    processing_time_ms: float
    raw_frame_shape: Optional[tuple] = None
    smoothed: bool = False
    no_face_detected: bool = False


# ── EmotionSmoother ───────────────────────────────────────────────────────────

class EmotionSmoother:
    """Rolling-window mode filter. Window=2 for near-instant reaction."""

    def __init__(self, window: int = SMOOTHER_WINDOW) -> None:
        self._window = window
        self._history: deque[str] = deque(maxlen=window)

    def update(self, raw_emotion: str) -> str:
        self._history.append(raw_emotion)
        try:
            return mode(self._history)
        except Exception:
            return raw_emotion

    def reset(self) -> None:
        self._history.clear()

    @property
    def is_warm(self) -> bool:
        return len(self._history) >= self._window


# ── Main detector class ───────────────────────────────────────────────────────

class FaceEmotionDetector:
    """
    Production-ready face-emotion detector.
    Default: FER + MTCNN (deep learning face detector).
    Fallback: DeepFace or Custom CNN.
    """

    EMOTIONS = EMOTIONS

    def __init__(
        self,
        backend: str = "fer",
        weights_path: str | Path = _DEFAULT_WEIGHTS,
        deepface_detector: str = "opencv",
        enforce_detection: bool = False,
        smoother_window: int = SMOOTHER_WINDOW,
    ) -> None:

        self.deepface_backend = deepface_detector
        self.enforce_detection = enforce_detection
        self._backend = backend

        # ── FER Face Detector ────────────────────────────────────────────────
        # FIX #1: Use mtcnn=True so MTCNN deep-learning detector is actually
        #         active. The original code had mtcnn=False in both branches,
        #         meaning MTCNN was never used despite the docstring claiming it.
        try:
            self._fer = FER(mtcnn=True)
            logger.info("FER initialized with MTCNN deep-learning detector ✓")
        except Exception as e:
            logger.warning("MTCNN init failed (%s), falling back to OpenCV detector", e)
            self._fer = FER(mtcnn=False)
            logger.info("FER initialized with OpenCV fallback ✓")

        # ── Haar Cascade (ultra-fast fallback for "is there a face?" check) ──
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        # ── Custom CNN setup ─────────────────────────────────────────────────
        self._cnn: Optional[FERCustomCNN] = None
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if backend == "custom_cnn":
            self._cnn = self._load_cnn(Path(weights_path))

        # ── Smoother ─────────────────────────────────────────────────────────
        self._smoother = EmotionSmoother(window=smoother_window)

        # ── Pre-warm the detection engine ────────────────────────────────────
        try:
            dummy = np.full((200, 200, 3), 128, dtype=np.uint8)
            cv2.ellipse(dummy, (100, 100), (60, 80), 0, 0, 360, (200, 180, 160), -1)
            self._fer.detect_emotions(dummy)
            logger.info("Face AI engine pre-warmed ✓")
        except Exception as e:
            logger.debug("Pre-warm note: %s", e)

        logger.info("FaceEmotionDetector v3.1 initialized [backend=%s]", self._backend)

    # ── Public API ────────────────────────────────────────────────────────────

    def detect_from_frame(self, frame: np.ndarray) -> EmotionResult:
        """Detect emotion from a BGR frame."""
        start = time.perf_counter()

        if frame is None or frame.size == 0:
            return self._empty_result(0.0, no_face=True)

        orig_h, orig_w = frame.shape[:2]

        # ── Internal Resize for speed ────────────────────────────────────────
        target_w = 320
        scale = target_w / orig_w
        target_h = int(orig_h * scale)
        small = cv2.resize(frame, (target_w, target_h))

        # ── Run inference ────────────────────────────────────────────────────
        emotion_data = None
        if self._backend == "custom_cnn" and self._cnn is not None:
            has_face, _ = self._run_haar(small)
            if has_face:
                emotion_data = self._run_custom_cnn(small)
        else:
            emotion_data = self._run_fer(small)

        # ── Fallback: If AI missed, report no face ───────────────────────────
        if emotion_data is None:
            elapsed = (time.perf_counter() - start) * 1000
            return self._empty_result(elapsed, no_face=True)

        elapsed = (time.perf_counter() - start) * 1000

        # ── Smooth ───────────────────────────────────────────────────────────
        smoothed = self._smoother.update(emotion_data["dominant_emotion"])

        # ── Build face region ─────────────────────────────────────────────────
        face_region = None
        if "box" in emotion_data and emotion_data["box"]:
            bx, by, bw, bh = emotion_data["box"]
            face_region = FaceRegion(
                x=int(bx / scale), y=int(by / scale),
                w=int(bw / scale), h=int(bh / scale),
                confidence=1.0,
            )

        return EmotionResult(
            dominant_emotion=smoothed,
            confidence=emotion_data["all_emotions"].get(smoothed, 0.0),
            all_emotions=emotion_data["all_emotions"],
            face_region=face_region,
            landmarks_detected=face_region is not None,
            processing_time_ms=round(elapsed, 2),
            raw_frame_shape=frame.shape,
            smoothed=self._smoother.is_warm,
            no_face_detected=False,
        )

    def detect_from_base64(self, b64_string: str) -> EmotionResult:
        """Decode base64 JPEG/PNG from React webcam and detect."""
        try:
            if "," in b64_string:
                b64_string = b64_string.split(",", 1)[1]

            # FIX #3: Strip whitespace/newlines before decoding.
            # Some base64 encoders insert line breaks every 76 chars; without
            # stripping, base64.b64decode raises binascii.Error.
            img_bytes = base64.b64decode(b64_string.strip())
            np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is None:
                return self._empty_result(0.0, no_face=True)
            return self.detect_from_frame(frame)
        except Exception as exc:
            logger.error("detect_from_base64 failed: %s", exc)
            return self._empty_result(0.0, no_face=True)

    def detect_from_image_path(self, path: str) -> EmotionResult:
        frame = cv2.imread(path)
        if frame is None:
            raise FileNotFoundError(f"Could not read image at: {path}")
        return self.detect_from_frame(frame)

    def compare_both_models(self, frame: np.ndarray) -> dict:
        df_res = self._run_deepface(frame)
        cnn_res = self._run_custom_cnn(frame) if self._cnn else None
        return {"deepface": df_res, "custom_cnn": cnn_res}

    def annotate_frame(self, frame: np.ndarray, result: EmotionResult) -> np.ndarray:
        annotated = frame.copy()
        if result.face_region:
            r = result.face_region
            cv2.rectangle(annotated, (r.x, r.y), (r.x + r.w, r.y + r.h), (0, 255, 0), 2)
        label = f"{result.dominant_emotion.upper()} {result.confidence:.0%}"
        cv2.putText(annotated, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        return annotated

    def reset_smoother(self) -> None:
        self._smoother.reset()

    def release(self) -> None:
        pass

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_cnn(self, path: Path) -> Optional[FERCustomCNN]:
        if not path.exists():
            logger.warning("Custom CNN weights not found at: %s", path)
            return None
        try:
            model = FERCustomCNN(num_classes=len(EMOTIONS))
            sd = torch.load(str(path), map_location=self._device, weights_only=True)
            model.load_state_dict(sd)
            model.to(self._device).eval()
            logger.info("Custom CNN loaded ✓")
            return model
        except Exception as e:
            logger.error("Custom CNN load failed: %s", e)
            return None

    def _run_haar(self, frame: np.ndarray) -> tuple[bool, Optional[FaceRegion]]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 3, minSize=(30, 30))
        if len(faces) == 0:
            return False, None
        x, y, w, h = faces[0]
        return True, FaceRegion(x=int(x), y=int(y), w=int(w), h=int(h), confidence=1.0)

    def _run_fer(self, frame: np.ndarray) -> Optional[dict]:
        """
        Run FER inference and return boosted emotion scores.

        FIX #2: Previously `all_emotions` returned the raw (unboosted) scores,
        while `dominant_emotion` was chosen from boosted scores. This caused
        the confidence value for the dominant emotion to appear artificially
        low (raw score < boosted score). Now `all_emotions` consistently
        returns the boosted scores so callers see the same values used for
        the dominance decision.
        """
        try:
            results = self._fer.detect_emotions(frame)
            if not results:
                return None
            raw_emotions = results[0]["emotions"]
            # Apply sensitivity multipliers
            boosted = {
                k: v * EMOTION_MULTIPLIERS.get(k, 1.0)
                for k, v in raw_emotions.items()
            }
            dominant = max(boosted, key=boosted.get)
            return {
                "dominant_emotion": dominant,
                "confidence": boosted.get(dominant, 0.0),
                "all_emotions": boosted,   # FIX: return boosted, not raw_emotions
                "box": results[0].get("box"),
            }
        except Exception as exc:
            logger.warning("FER failed: %s", exc)
            return None

    def _run_deepface(self, frame: np.ndarray) -> Optional[dict]:
        """
        Run DeepFace analysis with a timeout guard.

        FIX #5: DeepFace downloads model weights on the very first call and
        can hang for 30-60 s in restricted network environments. Wrapping the
        call in a thread + timeout means the endpoint stays responsive.
        """
        import concurrent.futures

        def _call():
            return DeepFace.analyze(
                frame,
                actions=["emotion"],
                detector_backend=self.deepface_backend,
                enforce_detection=self.enforce_detection,
                silent=True,
            )

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_call)
                analysis = future.result(timeout=_DEEPFACE_TIMEOUT)

            if isinstance(analysis, list):
                analysis = analysis[0]
            emotions = analysis["emotion"]
            dominant = analysis["dominant_emotion"]
            total = sum(emotions.values()) or 1.0
            norm = {k: round(v / total, 4) for k, v in emotions.items()}
            return {
                "dominant_emotion": dominant,
                "confidence": norm.get(dominant, 0.0),
                "all_emotions": norm,
            }
        except concurrent.futures.TimeoutError:
            logger.warning("DeepFace timed out after %ss", _DEEPFACE_TIMEOUT)
            return None
        except Exception as exc:
            logger.warning("DeepFace failed: %s", exc)
            return None

    def _run_custom_cnn(self, frame: np.ndarray) -> Optional[dict]:
        if self._cnn is None:
            return None
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (FER_IMG_SIZE, FER_IMG_SIZE))
            tensor = torch.from_numpy(resized).float() / 255.0
            tensor = tensor.unsqueeze(0).unsqueeze(0).to(self._device)
            with torch.no_grad():
                probs = self._cnn.predict_proba(tensor)[0].cpu().numpy()
            idx = int(np.argmax(probs))
            return {
                "dominant_emotion": EMOTIONS[idx],
                "confidence": float(probs[idx]),
                "all_emotions": {EMOTIONS[i]: float(probs[i]) for i in range(len(EMOTIONS))},
            }
        except Exception as exc:
            logger.warning("Custom CNN inference failed: %s", exc)
            return None

    def _empty_result(self, elapsed_ms: float, face_region=None, no_face=False) -> EmotionResult:
        return EmotionResult(
            dominant_emotion="neutral",
            confidence=0.0,
            all_emotions={e: 0.0 for e in EMOTIONS},
            face_region=face_region,
            landmarks_detected=False,
            processing_time_ms=elapsed_ms,
            no_face_detected=no_face,
        )