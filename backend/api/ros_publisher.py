"""
ros_publisher.py
----------------
Publishes emotion-based speech commands to the ROS2 /speech topic via WSL.

Rules:
  - Neutral emotion is IGNORED — never published.
  - After a successful publish, a 20-second cooldown is enforced before
    the next emotion can be published (prevents ROS2 spam every frame).
  - The subprocess runs in WSL so it can reach the ROS2 environment.
"""

import subprocess
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Emotion → speech phrase mapping ──────────────────────────────────────────

EMOTION_PHRASES: dict[str, str] = {
    "happy":    "I am happy, I am very happy, I am feeling really great today!",
    "sad":      "I am sad, I am very sad, I am feeling quite down right now.",
    "angry":    "I am angry, I am very angry, I am feeling very furious right now.",
    "fear":     "I am scared, I feel afraid, something is making me very fearful.",
    "fearful":  "I am scared, I feel afraid, something is making me very fearful.",
    "surprise": "Oh wow, I am so surprised, I really did not see that coming!",
    "surprised":"Oh wow, I am so surprised, I really did not see that coming!",
    "disgust":  "I feel disgusted, this is quite unpleasant for me.",
}

# ── Cooldown state ────────────────────────────────────────────────────────────

_COOLDOWN_SECONDS = 20
_last_publish_time: float = 0.0       # Unix timestamp of last successful publish
_last_published_emotion: Optional[str] = None


def publish_emotion_to_ros(emotion: str) -> bool:
    """
    Publishes a speech command to the ROS2 /speech topic via WSL.

    Returns True if the command was sent, False if skipped (neutral / cooldown).
    """
    global _last_publish_time, _last_published_emotion

    emotion = emotion.lower().strip()

    # 1. Skip neutral entirely
    if emotion == "neutral" or emotion not in EMOTION_PHRASES:
        logger.debug("ROS publisher: skipping emotion '%s' (neutral or unmapped).", emotion)
        return False

    # 2. Enforce 20-second cooldown
    now = time.monotonic()
    elapsed = now - _last_publish_time
    if elapsed < _COOLDOWN_SECONDS:
        remaining = round(_COOLDOWN_SECONDS - elapsed, 1)
        logger.debug(
            "ROS publisher: cooldown active (%.1fs remaining). Skipping '%s'.",
            remaining, emotion,
        )
        return False

    phrase = EMOTION_PHRASES[emotion]
    ros_data = f"speaking:{phrase}"

    # Escape single quotes inside the phrase for bash safety
    ros_data_escaped = ros_data.replace("'", "'\\''")

    bash_cmd = (
        "source /opt/ros/humble/setup.bash && "
        f"ros2 topic pub -1 /speech std_msgs/msg/String "
        f"\"{{data: '{ros_data_escaped}'}}\""
    )

    try:
        logger.info("ROS publisher: publishing emotion='%s' → '%s'", emotion, phrase)
        subprocess.Popen(
            ["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-c", bash_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Update cooldown state
        _last_publish_time = now
        _last_published_emotion = emotion
        logger.info("ROS publisher: command dispatched to WSL successfully.")
        return True

    except Exception as exc:
        logger.error("ROS publisher: failed to dispatch WSL command: %s", exc)
        return False
