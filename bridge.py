#!/usr/bin/env python3
"""
EmoBot Bridge v3.1 - File-Watcher Edition
=========================================
Pipeline: ROS2 → Python → HTTP API + JSON File → Unreal Engine
Emotions: happy, sad, angry, fearful, surprised, calm, neutral
Features:
  - Writes /speech to input.json for Unreal Engine local polling
  - Face morph targets (MetaHuman blend shapes)
  - Body pose rotations (head, neck, spine)
  - Environment lighting colors
  - Lip sync visemes
  - Dance/movement sequences
  - Smooth emotion transitions
  - Manual override API for testing
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import JointState
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import threading
import time
import math
import os
import json

# ================================================================
# CONFIGURATION
# ================================================================
# In WSL, the D: drive is mapped to /mnt/d/
UNREAL_JSON_PATH = "/mnt/d/Unreal_Projects/Final_V2/input.json"

# ================================================================
# FASTAPI APP
# ================================================================
app = FastAPI(
    title="EmoBot Bridge v3.1",
    description="ROS2 to Unreal Engine emotion bridge with File-Watcher",
    version="3.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================================
# EMOTION → FACE MORPH TARGET MAP
# ================================================================
EMOTION_FACE_MAP = {
    "happy": {
        "CTRL_expressions_mouthSmileL":     0.90,
        "CTRL_expressions_mouthSmileR":     0.90,
        "CTRL_expressions_cheekSquintL":    0.70,
        "CTRL_expressions_cheekSquintR":    0.70,
        "CTRL_expressions_eyeSquintL":      0.45,
        "CTRL_expressions_eyeSquintR":      0.45,
        "CTRL_expressions_browInnerUpL":    0.25,
        "CTRL_expressions_browInnerUpR":    0.25,
        "CTRL_expressions_mouthFrownL":     0.00,
        "CTRL_expressions_mouthFrownR":     0.00,
        "CTRL_expressions_browDownL":       0.00,
        "CTRL_expressions_browDownR":       0.00,
        "CTRL_expressions_mouthPressL":     0.00,
        "CTRL_expressions_mouthPressR":     0.00,
        "CTRL_expressions_noseSneerL":      0.00,
        "CTRL_expressions_noseSneerR":      0.00,
        "CTRL_expressions_jawOpen":         0.10,
        "CTRL_expressions_eyeWideL":        0.20,
        "CTRL_expressions_eyeWideR":        0.20,
    },
    "sad": {
        "CTRL_expressions_mouthFrownL":     0.85,
        "CTRL_expressions_mouthFrownR":     0.85,
        "CTRL_expressions_browInnerUpL":    0.90,
        "CTRL_expressions_browInnerUpR":    0.90,
        "CTRL_expressions_mouthPressL":     0.30,
        "CTRL_expressions_mouthPressR":     0.30,
        "CTRL_expressions_eyeSquintL":      0.20,
        "CTRL_expressions_eyeSquintR":      0.20,
        "CTRL_expressions_jawOpen":         0.10,
        "CTRL_expressions_mouthSmileL":     0.00,
        "CTRL_expressions_mouthSmileR":     0.00,
        "CTRL_expressions_cheekSquintL":    0.00,
        "CTRL_expressions_cheekSquintR":    0.00,
        "CTRL_expressions_browDownL":       0.00,
        "CTRL_expressions_browDownR":       0.00,
        "CTRL_expressions_eyeWideL":        0.00,
        "CTRL_expressions_eyeWideR":        0.00,
        "CTRL_expressions_noseSneerL":      0.00,
        "CTRL_expressions_noseSneerR":      0.00,
    },
    "angry": {
        "CTRL_expressions_browDownL":       0.95,
        "CTRL_expressions_browDownR":       0.95,
        "CTRL_expressions_noseSneerL":      0.60,
        "CTRL_expressions_noseSneerR":      0.60,
        "CTRL_expressions_mouthPressL":     0.50,
        "CTRL_expressions_mouthPressR":     0.50,
        "CTRL_expressions_mouthFrownL":     0.40,
        "CTRL_expressions_mouthFrownR":     0.40,
        "CTRL_expressions_eyeSquintL":      0.70,
        "CTRL_expressions_eyeSquintR":      0.70,
        "CTRL_expressions_cheekSquintL":    0.30,
        "CTRL_expressions_cheekSquintR":    0.30,
        "CTRL_expressions_mouthSmileL":     0.00,
        "CTRL_expressions_mouthSmileR":     0.00,
        "CTRL_expressions_browInnerUpL":    0.00,
        "CTRL_expressions_browInnerUpR":    0.00,
        "CTRL_expressions_eyeWideL":        0.00,
        "CTRL_expressions_eyeWideR":        0.00,
        "CTRL_expressions_jawOpen":         0.05,
    },
    "fearful": {
        "CTRL_expressions_eyeWideL":        0.95,
        "CTRL_expressions_eyeWideR":        0.95,
        "CTRL_expressions_browInnerUpL":    0.85,
        "CTRL_expressions_browInnerUpR":    0.85,
        "CTRL_expressions_browOuterUpL":    0.70,
        "CTRL_expressions_browOuterUpR":    0.70,
        "CTRL_expressions_jawOpen":         0.35,
        "CTRL_expressions_mouthFrownL":     0.45,
        "CTRL_expressions_mouthFrownR":     0.45,
        "CTRL_expressions_mouthStretchL":   0.50,
        "CTRL_expressions_mouthStretchR":   0.50,
        "CTRL_expressions_mouthSmileL":     0.00,
        "CTRL_expressions_mouthSmileR":     0.00,
        "CTRL_expressions_browDownL":       0.00,
        "CTRL_expressions_browDownR":       0.00,
        "CTRL_expressions_eyeSquintL":      0.00,
        "CTRL_expressions_eyeSquintR":      0.00,
        "CTRL_expressions_noseSneerL":      0.00,
        "CTRL_expressions_noseSneerR":      0.00,
    },
    "surprised": {
        "CTRL_expressions_eyeWideL":        1.00,
        "CTRL_expressions_eyeWideR":        1.00,
        "CTRL_expressions_browInnerUpL":    1.00,
        "CTRL_expressions_browInnerUpR":    1.00,
        "CTRL_expressions_browOuterUpL":    0.90,
        "CTRL_expressions_browOuterUpR":    0.90,
        "CTRL_expressions_jawOpen":         0.65,
        "CTRL_expressions_mouthFrownL":     0.10,
        "CTRL_expressions_mouthFrownR":     0.10,
        "CTRL_expressions_mouthSmileL":     0.00,
        "CTRL_expressions_mouthSmileR":     0.00,
        "CTRL_expressions_browDownL":       0.00,
        "CTRL_expressions_browDownR":       0.00,
        "CTRL_expressions_eyeSquintL":      0.00,
        "CTRL_expressions_eyeSquintR":      0.00,
        "CTRL_expressions_noseSneerL":      0.00,
        "CTRL_expressions_noseSneerR":      0.00,
        "CTRL_expressions_cheekSquintL":    0.00,
        "CTRL_expressions_cheekSquintR":    0.00,
    },
    "calm": {
        "CTRL_expressions_mouthSmileL":     0.25,
        "CTRL_expressions_mouthSmileR":     0.25,
        "CTRL_expressions_eyeSquintL":      0.10,
        "CTRL_expressions_eyeSquintR":      0.10,
        "CTRL_expressions_cheekSquintL":    0.15,
        "CTRL_expressions_cheekSquintR":    0.15,
        "CTRL_expressions_mouthFrownL":     0.00,
        "CTRL_expressions_mouthFrownR":     0.00,
        "CTRL_expressions_browDownL":       0.00,
        "CTRL_expressions_browDownR":       0.00,
        "CTRL_expressions_browInnerUpL":    0.05,
        "CTRL_expressions_browInnerUpR":    0.05,
        "CTRL_expressions_eyeWideL":        0.00,
        "CTRL_expressions_eyeWideR":        0.00,
        "CTRL_expressions_jawOpen":         0.00,
        "CTRL_expressions_noseSneerL":      0.00,
        "CTRL_expressions_noseSneerR":      0.00,
    },
    "neutral": {
        "CTRL_expressions_mouthSmileL":     0.00,
        "CTRL_expressions_mouthSmileR":     0.00,
        "CTRL_expressions_mouthFrownL":     0.00,
        "CTRL_expressions_mouthFrownR":     0.00,
        "CTRL_expressions_browInnerUpL":    0.00,
        "CTRL_expressions_browInnerUpR":    0.00,
        "CTRL_expressions_browOuterUpL":    0.00,
        "CTRL_expressions_browOuterUpR":    0.00,
        "CTRL_expressions_browDownL":       0.00,
        "CTRL_expressions_browDownR":       0.00,
        "CTRL_expressions_eyeSquintL":      0.00,
        "CTRL_expressions_eyeSquintR":      0.00,
        "CTRL_expressions_eyeWideL":        0.00,
        "CTRL_expressions_eyeWideR":        0.00,
        "CTRL_expressions_cheekSquintL":    0.00,
        "CTRL_expressions_cheekSquintR":    0.00,
        "CTRL_expressions_noseSneerL":      0.00,
        "CTRL_expressions_noseSneerR":      0.00,
        "CTRL_expressions_mouthPressL":     0.00,
        "CTRL_expressions_mouthPressR":     0.00,
        "CTRL_expressions_mouthStretchL":   0.00,
        "CTRL_expressions_mouthStretchR":   0.00,
        "CTRL_expressions_jawOpen":         0.00,
        "CTRL_expressions_mouthPucker":     0.00,
        "CTRL_expressions_mouthClose":      0.00,
    }
}

# ================================================================
# EMOTION → BODY POSE MAP
# ================================================================
EMOTION_BODY_MAP = {
    "happy": {
        "head_pitch":   -8.0,
        "head_yaw":      3.0,
        "head_roll":     4.0,
        "neck_pitch":   -4.0,
        "spine_pitch":  -3.0,
        "description":  "Upright confident happy pose"
    },
    "sad": {
        "head_pitch":   18.0,
        "head_yaw":     -3.0,
        "head_roll":    -6.0,
        "neck_pitch":   12.0,
        "spine_pitch":  10.0,
        "description":  "Slumped sad pose"
    },
    "angry": {
        "head_pitch":    8.0,
        "head_yaw":      0.0,
        "head_roll":     0.0,
        "neck_pitch":    5.0,
        "spine_pitch":  -6.0,
        "description":  "Aggressive forward lean"
    },
    "fearful": {
        "head_pitch":   10.0,
        "head_yaw":    -15.0,
        "head_roll":    -8.0,
        "neck_pitch":    8.0,
        "spine_pitch":   6.0,
        "description":  "Cowering fearful pose"
    },
    "surprised": {
        "head_pitch":  -12.0,
        "head_yaw":      0.0,
        "head_roll":     0.0,
        "neck_pitch":   -6.0,
        "spine_pitch":  -4.0,
        "description":  "Recoiled surprise pose"
    },
    "calm": {
        "head_pitch":    0.0,
        "head_yaw":      2.0,
        "head_roll":     2.0,
        "neck_pitch":    0.0,
        "spine_pitch":   0.0,
        "description":  "Relaxed neutral calm pose"
    },
    "neutral": {
        "head_pitch":    0.0,
        "head_yaw":      0.0,
        "head_roll":     0.0,
        "neck_pitch":    0.0,
        "spine_pitch":   0.0,
        "description":  "Default neutral pose"
    }
}

# ================================================================
# EMOTION → ENVIRONMENT LIGHTING
# ================================================================
EMOTION_COLOR_MAP = {
    "happy":     {"r": 1.00, "g": 0.85, "b": 0.20, "intensity": 2.5, "fog": 0.0},
    "sad":       {"r": 0.20, "g": 0.35, "b": 0.90, "intensity": 0.7, "fog": 0.3},
    "angry":     {"r": 0.95, "g": 0.10, "b": 0.05, "intensity": 3.0, "fog": 0.0},
    "fearful":   {"r": 0.35, "g": 0.15, "b": 0.55, "intensity": 0.8, "fog": 0.4},
    "surprised": {"r": 0.80, "g": 0.30, "b": 0.95, "intensity": 2.2, "fog": 0.0},
    "calm":      {"r": 0.40, "g": 0.80, "b": 0.70, "intensity": 1.2, "fog": 0.1},
    "neutral":   {"r": 0.90, "g": 0.90, "b": 0.90, "intensity": 1.5, "fog": 0.0},
}

# ================================================================
# VISEME MAP FOR LIP SYNC
# ================================================================
VISEME_MAP = {
    "rest": {
        "CTRL_expressions_jawOpen":     0.00,
        "CTRL_expressions_mouthClose":  0.80,
        "CTRL_expressions_mouthPucker": 0.00,
    },
    "aa": {
        "CTRL_expressions_jawOpen":     0.75,
        "CTRL_expressions_mouthClose":  0.00,
        "CTRL_expressions_mouthPucker": 0.00,
    },
    "ee": {
        "CTRL_expressions_jawOpen":     0.30,
        "CTRL_expressions_mouthSmileL": 0.60,
        "CTRL_expressions_mouthSmileR": 0.60,
        "CTRL_expressions_mouthClose":  0.00,
    },
    "ih": {
        "CTRL_expressions_jawOpen":     0.25,
        "CTRL_expressions_mouthClose":  0.10,
        "CTRL_expressions_mouthPucker": 0.00,
    },
    "oh": {
        "CTRL_expressions_jawOpen":     0.50,
        "CTRL_expressions_mouthPucker": 0.55,
        "CTRL_expressions_mouthClose":  0.00,
    },
    "ou": {
        "CTRL_expressions_jawOpen":     0.25,
        "CTRL_expressions_mouthPucker": 0.80,
        "CTRL_expressions_mouthClose":  0.00,
    },
    "pp": {
        "CTRL_expressions_jawOpen":     0.00,
        "CTRL_expressions_mouthClose":  1.00,
        "CTRL_expressions_mouthPressL": 0.60,
        "CTRL_expressions_mouthPressR": 0.60,
    },
    "ff": {
        "CTRL_expressions_jawOpen":     0.10,
        "CTRL_expressions_mouthClose":  0.40,
        "CTRL_expressions_mouthPressL": 0.20,
        "CTRL_expressions_mouthPressR": 0.20,
    },
    "th": {
        "CTRL_expressions_jawOpen":     0.15,
        "CTRL_expressions_mouthClose":  0.20,
    },
    "ss": {
        "CTRL_expressions_jawOpen":     0.08,
        "CTRL_expressions_mouthClose":  0.70,
        "CTRL_expressions_mouthSmileL": 0.15,
        "CTRL_expressions_mouthSmileR": 0.15,
    },
}

# ================================================================
# MOVEMENT SEQUENCES
# ================================================================
MOVEMENT_SEQUENCES = {
    "happy": {
        "head_bob_amplitude":   3.0,
        "head_bob_speed":       1.5,
        "head_sway_amplitude":  2.0,
        "head_sway_speed":      0.8,
        "breathing_amplitude":  1.5,
        "breathing_speed":      0.4,
        "description": "Energetic happy bouncing"
    },
    "sad": {
        "head_bob_amplitude":   0.5,
        "head_bob_speed":       0.2,
        "head_sway_amplitude":  0.5,
        "head_sway_speed":      0.1,
        "breathing_amplitude":  2.0,
        "breathing_speed":      0.15,
        "description": "Slow heavy sad movements"
    },
    "angry": {
        "head_bob_amplitude":   0.0,
        "head_bob_speed":       0.0,
        "head_sway_amplitude":  1.0,
        "head_sway_speed":      2.0,
        "breathing_amplitude":  3.0,
        "breathing_speed":      0.6,
        "description": "Tense rigid angry micro-tremors"
    },
    "fearful": {
        "head_bob_amplitude":   0.5,
        "head_bob_speed":       3.0,
        "head_sway_amplitude":  1.5,
        "head_sway_speed":      2.5,
        "breathing_amplitude":  2.5,
        "breathing_speed":      0.8,
        "description": "Trembling fear movements"
    },
    "surprised": {
        "head_bob_amplitude":   2.0,
        "head_bob_speed":       0.5,
        "head_sway_amplitude":  1.0,
        "head_sway_speed":      0.5,
        "breathing_amplitude":  1.0,
        "breathing_speed":      0.3,
        "description": "Startled then settling"
    },
    "calm": {
        "head_bob_amplitude":   0.5,
        "head_bob_speed":       0.3,
        "head_sway_amplitude":  0.8,
        "head_sway_speed":      0.2,
        "breathing_amplitude":  1.0,
        "breathing_speed":      0.2,
        "description": "Peaceful minimal movement"
    },
    "neutral": {
        "head_bob_amplitude":   1.0,
        "head_bob_speed":       0.4,
        "head_sway_amplitude":  0.8,
        "head_sway_speed":      0.3,
        "breathing_amplitude":  1.0,
        "breathing_speed":      0.25,
        "description": "Normal relaxed breathing"
    }
}

# ================================================================
# GLOBAL STATE
# ================================================================
app_state = {
    "emotion": {
        "type":      "neutral",
        "intensity":  1.0,
        "previous":  "neutral",
        "timestamp":  0.0,
        "confidence": 0.0,
    },
    "face_morphs":   EMOTION_FACE_MAP["neutral"].copy(),
    "body_pose":     EMOTION_BODY_MAP["neutral"].copy(),
    "environment":   EMOTION_COLOR_MAP["neutral"].copy(),
    "movement":      MOVEMENT_SEQUENCES["neutral"].copy(),
    "live_movement": {
        "head_pitch_offset": 0.0,
        "head_yaw_offset":   0.0,
        "head_roll_offset":  0.0,
        "spine_offset":      0.0,
    },
    "speech": {
        "is_speaking":   False,
        "current_text":  "",
        "viseme":        "rest",
        "viseme_morphs": VISEME_MAP["rest"].copy(),
    },
    "joints": {
        "head_pitch":  0.0,
        "head_yaw":    0.0,
        "head_roll":   0.0,
        "neck_pitch":  0.0,
        "neck_yaw":    0.0,
        "spine_pitch": 0.0,
    },
    "system": {
        "bridge_version": "3.1",
        "ros_connected":  True,
        "uptime":         0.0,
        "start_time":     time.time(),
        "total_emotions_received": 0,
    }
}

START_TIME = time.time()

# ================================================================
# FILE WRITER HELPER (NEW)
# ================================================================
def write_to_unreal_file(text):
    """Writes the speech text to the local input.json file for Unreal to watch."""
    try:
        data = {"text": text}
        # Ensure the directory exists before attempting to write
        os.makedirs(os.path.dirname(UNREAL_JSON_PATH), exist_ok=True)
        
        with open(UNREAL_JSON_PATH, 'w') as f:
            json.dump(data, f)
#        print(f"📁 Local JSON Updated: {text}")
    except Exception as e:
        print(f"❌ Error writing to input.json: {e}")

# ================================================================
# MOVEMENT ANIMATION THREAD
# ================================================================
def movement_animation_loop():
    while True:
        try:
            t = time.time() - START_TIME
            seq = app_state["movement"]

            bob_amp   = seq.get("head_bob_amplitude",  1.0)
            bob_spd   = seq.get("head_bob_speed",      0.4)
            sway_amp  = seq.get("head_sway_amplitude", 0.8)
            sway_spd  = seq.get("head_sway_speed",     0.3)
            breath_amp = seq.get("breathing_amplitude", 1.0)
            breath_spd = seq.get("breathing_speed",    0.25)

            head_pitch_offset = math.sin(t * bob_spd * 2 * math.pi) * bob_amp
            head_yaw_offset = math.sin(t * sway_spd * 2 * math.pi) * sway_amp
            spine_offset = math.sin(t * breath_spd * 2 * math.pi) * breath_amp

            app_state["live_movement"] = {
                "head_pitch_offset": round(head_pitch_offset, 3),
                "head_yaw_offset":   round(head_yaw_offset, 3),
                "head_roll_offset":  0.0,
                "spine_offset":      round(spine_offset, 3),
            }

            app_state["system"]["uptime"] = round(time.time() - START_TIME, 1)
            time.sleep(0.033)

        except Exception as e:
            print(f"Movement loop error: {e}")
            time.sleep(0.1)

# ================================================================
# CORE STATE UPDATE FUNCTION
# ================================================================
def update_emotion_state(emotion_type: str, intensity: float = 1.0, confidence: float = 1.0):
    emotion_type = emotion_type.lower().strip()

    if emotion_type not in EMOTION_FACE_MAP:
        print(f"⚠️  Unknown emotion '{emotion_type}', defaulting to neutral")
        emotion_type = "neutral"

    intensity = max(0.0, min(1.0, intensity))
    previous = app_state["emotion"]["type"]

    app_state["emotion"]["previous"]   = previous
    app_state["emotion"]["type"]       = emotion_type
    app_state["emotion"]["intensity"]  = intensity
    app_state["emotion"]["confidence"] = confidence
    app_state["emotion"]["timestamp"]  = time.time()
    app_state["system"]["total_emotions_received"] += 1

    face_morphs = {}
    for morph_name, morph_value in EMOTION_FACE_MAP[emotion_type].items():
        face_morphs[morph_name] = round(morph_value * intensity, 4)
    app_state["face_morphs"] = face_morphs

    body = EMOTION_BODY_MAP[emotion_type].copy()
    for key in ["head_pitch", "head_yaw", "head_roll", "neck_pitch", "spine_pitch"]:
        body[key] = round(body[key] * intensity, 2)
    app_state["body_pose"] = body

    env = EMOTION_COLOR_MAP[emotion_type].copy()
    env["intensity"] = round(env["intensity"] * intensity, 2)
    app_state["environment"] = env

    app_state["movement"] = MOVEMENT_SEQUENCES[emotion_type].copy()

    print(f"\n{'='*50}")
    print(f"🎭 EMOTION: {emotion_type.upper()} (intensity: {intensity})")
    print(f"   Previous: {previous}")
    print(f"   Face morphs: {len(face_morphs)} values set")
    print(f"   Head pitch: {body['head_pitch']}°")
    print(f"   Light: R={env['r']}, G={env['g']}, B={env['b']}")
    print(f"{'='*50}\n")

# ================================================================
# ROS2 NODE
# ================================================================
class EmoBotBridge(Node):
    def __init__(self):
        super().__init__('emobot_bridge_v3')
        self.emotion_sub = self.create_subscription(String, '/emotion', self.emotion_callback, 10)
        self.joint_sub = self.create_subscription(JointState, '/joint_states', self.joint_callback, 10)
        self.speech_sub = self.create_subscription(String, '/speech', self.speech_callback, 10)
        self.viseme_sub = self.create_subscription(String, '/viseme', self.viseme_callback, 10)
        
        self.get_logger().info('🤖 EmoBot Bridge v3.1 READY! (File-Watcher Active)')
        self.get_logger().info('📡 Topics: /emotion, /joint_states, /speech, /viseme')

    def emotion_callback(self, msg: String):
        try:
            parts = msg.data.strip().split(':')
            emotion_type = parts[0].strip()
            intensity    = float(parts[1]) if len(parts) > 1 else 1.0
            confidence   = float(parts[2]) if len(parts) > 2 else 1.0
            update_emotion_state(emotion_type, intensity, confidence)
        except Exception as e:
            self.get_logger().error(f'Emotion parse error: {e} | msg: {msg.data}')

    def joint_callback(self, msg: JointState):
        try:
            for i, name in enumerate(msg.name):
                if name in app_state["joints"]:
                    app_state["joints"][name] = round(float(msg.position[i]), 4)
        except Exception as e:
            self.get_logger().error(f'Joint parse error: {e}')

    def speech_callback(self, msg: String):
        try:
            parts = msg.data.strip().split(':', 1)
            cmd   = parts[0].strip()

            if cmd == 'speaking':
                text = parts[1] if len(parts) > 1 else ""
                app_state["speech"]["is_speaking"]  = True
                app_state["speech"]["current_text"] = text
                
                # Update Unreal JSON File
                write_to_unreal_file(text)
                
                self.get_logger().info(f'🎤 Speaking...')

            elif cmd == 'stop':
                app_state["speech"]["is_speaking"]   = False
                app_state["speech"]["current_text"]  = ""
                app_state["speech"]["viseme"]        = "rest"
                app_state["speech"]["viseme_morphs"] = VISEME_MAP["rest"].copy()
                self.get_logger().info('🎤 Stopped speaking')

        except Exception as e:
            self.get_logger().error(f'Speech parse error: {e}')

    def viseme_callback(self, msg: String):
        try:
            viseme = msg.data.strip().lower()
            if viseme in VISEME_MAP:
                app_state["speech"]["viseme"]        = viseme
                app_state["speech"]["viseme_morphs"] = VISEME_MAP[viseme].copy()
            else:
                self.get_logger().warn(f'Unknown viseme: {viseme}')
        except Exception as e:
            self.get_logger().error(f'Viseme error: {e}')

# ================================================================
# FASTAPI ENDPOINTS
# ================================================================

@app.get("/")
def root():
    return {
        "status": "running",
        "version": "3.1",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "current_emotion": app_state["emotion"]["type"],
        "emotions_available": list(EMOTION_FACE_MAP.keys()),
        "endpoints": [
            "GET  /state        - Full state",
            "GET  /face         - Face morph values only",
            "GET  /body         - Body pose rotations",
            "GET  /movement     - Live movement offsets",
            "GET  /environment  - Lighting colors",
            "GET  /speech       - Speech and lip sync state",
            "POST /emotion/{type}?intensity=0.8 - Set emotion manually",
            "POST /speech/start?text=Hello      - Start speaking",
            "POST /speech/stop                  - Stop speaking",
        ]
    }

@app.get("/state")
def get_full_state():
    return {
        "emotion":      app_state["emotion"],
        "face_morphs":  app_state["face_morphs"],
        "body_pose":    app_state["body_pose"],
        "movement":     app_state["live_movement"],
        "environment":  app_state["environment"],
        "speech":       app_state["speech"],
        "system":       app_state["system"],
    }

@app.get("/face")
def get_face_morphs():
    combined = {}
    combined.update(app_state["face_morphs"])

    if app_state["speech"]["is_speaking"]:
        viseme_morphs = app_state["speech"]["viseme_morphs"]
        for key, val in viseme_morphs.items():
            if key in combined:
                combined[key] = max(combined[key], val)
            else:
                combined[key] = val

    return combined

@app.get("/body")
def get_body_pose():
    base    = app_state["body_pose"]
    live    = app_state["live_movement"]

    return {
        "head_pitch":  round(base.get("head_pitch",  0) + live["head_pitch_offset"], 3),
        "head_yaw":    round(base.get("head_yaw",    0) + live["head_yaw_offset"],   3),
        "head_roll":   round(base.get("head_roll",   0) + live["head_roll_offset"],  3),
        "neck_pitch":  round(base.get("neck_pitch",  0) + live["spine_offset"] * 0.5, 3),
        "spine_pitch": round(base.get("spine_pitch", 0) + live["spine_offset"],      3),
        "description": base.get("description", ""),
    }

@app.get("/environment")
def get_environment():
    return app_state["environment"]

@app.get("/movement")
def get_movement():
    return {
        "live":     app_state["live_movement"],
        "sequence": app_state["movement"],
    }

@app.get("/speech")
def get_speech():
    return app_state["speech"]

@app.get("/emotion")
def get_emotion():
    return app_state["emotion"]

@app.post("/emotion/{emotion_type}")
def set_emotion_api(
    emotion_type: str,
    intensity:    float = 1.0,
    confidence:   float = 1.0
):
    update_emotion_state(emotion_type, intensity, confidence)
    return {
        "success": True,
        "emotion": app_state["emotion"],
        "morphs_set": len(app_state["face_morphs"]),
    }

@app.post("/speech/start")
def start_speaking(text: str = ""):
    app_state["speech"]["is_speaking"]  = True
    app_state["speech"]["current_text"] = text
    
    # Update Unreal JSON File
    write_to_unreal_file(text)
    
    return {"success": True, "text": text}

@app.post("/speech/stop")
def stop_speaking():
    app_state["speech"]["is_speaking"]   = False
    app_state["speech"]["current_text"]  = ""
    app_state["speech"]["viseme"]        = "rest"
    app_state["speech"]["viseme_morphs"] = VISEME_MAP["rest"].copy()
    return {"success": True}

@app.get("/debug")
def debug():
    return {
        "full_state":    app_state,
        "face_map":      EMOTION_FACE_MAP,
        "body_map":      EMOTION_BODY_MAP,
        "color_map":     EMOTION_COLOR_MAP,
        "movement_map":  MOVEMENT_SEQUENCES,
    }

# ================================================================
# ROS2 THREAD
# ================================================================
def run_ros2():
    rclpy.init()
    node = EmoBotBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

# ================================================================
# MAIN
# ================================================================
if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  🚀 EmoBot Bridge v3.1 — File-Watcher Edition")
    print("  📡 ROS2 → Python → JSON File → Unreal Engine")
    print("=" * 55)
    print(f"\n  Emotions: {', '.join(EMOTION_FACE_MAP.keys())}")
    print(f"  Face morphs per emotion: ~12-16 values")
    print(f"  Movement: breathing + head bob + sway")
    print(f"  File Target: {UNREAL_JSON_PATH}")
    print("\n  Endpoints:")
    print("    GET  http://0.0.0.0:8000/state")
    print("    GET  http://0.0.0.0:8000/face")
    print("    POST http://0.0.0.0:8000/emotion/happy?intensity=0.9")
    print("=" * 55 + "\n")

    movement_thread = threading.Thread(
        target=movement_animation_loop,
        daemon=True
    )
    movement_thread.start()
    print("✅ Movement animation thread started")

    ros_thread = threading.Thread(target=run_ros2, daemon=True)
    ros_thread.start()
    print("✅ ROS2 subscriber thread started")

    print("✅ Starting HTTP server on port 8000...\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")	
