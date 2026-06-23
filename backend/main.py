"""
main.py
-------
Main entry point for the Emotion Robot Backend.
Integrates Member 1 (AI/Memory), Member 2 (Voice/Auth), and Member 3 (Frontend/UX).
"""

import os
import logging
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# --- Project Imports ---
from database.db import engine, Base, get_db
from database.models import User, Interaction
from dependencies import get_current_user

# --- Route Imports ---
from auth.routes import router as auth_router
from api.routes_chat import router as chat_router
from api.routes_emotion import router as emotion_router
from api.memory import router as memory_router
from api.context_graph import router as context_router
from api.explainability import router as explain_router
from api.m2_tasks import router as m2_router
from api.routes_bridge import router as bridge_router
from api.routes_convai import router as convai_router

# ─────────────────────────────────────────────
# Setup and Configuration
# ─────────────────────────────────────────────

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

# Create Database Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Emotion-Aware Conversational Robot System",
    description="Unified Backend for AI, Memory, Voice, and 3D Interaction.",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include Routers ─────────────────────────────────────────────────────────

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat_router)
app.include_router(emotion_router)
app.include_router(memory_router)
app.include_router(context_router)
app.include_router(explain_router)
app.include_router(m2_router)
app.include_router(bridge_router)
app.include_router(convai_router, prefix="/api/convai", tags=["ConvAI"])

# Alias for Analytics Dashboard compatibility — properly use router instead of calling DI function directly
@app.get("/api/user/stats")
async def user_stats_alias(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from sqlalchemy import func
    from database.models import Session as UserSession, Interaction
    from dependencies import memory_store

    total_sessions = db.query(UserSession).filter(UserSession.user_id == current_user.id).count()
    total_interactions = db.query(Interaction).join(UserSession).filter(UserSession.user_id == current_user.id).count()

    emotion_counts = db.query(
        Interaction.emotion_detected,
        func.count(Interaction.emotion_detected)
    ).join(UserSession).filter(UserSession.user_id == current_user.id).group_by(Interaction.emotion_detected).all()

    counts_dict = {e: c for e, c in emotion_counts if e}
    STANDARD_EMOTIONS = ["happy", "sad", "angry", "fearful", "surprised", "calm", "neutral"]
    full_breakdown = {e: counts_dict.get(e, 0) for e in STANDARD_EMOTIONS}

    favorite_emotion = "neutral"
    valid_counts = [x for x in emotion_counts if x[0]]
    if valid_counts:
        favorite_emotion = max(valid_counts, key=lambda x: x[1])[0]

    total_memories = 0
    try:
        total_memories = memory_store.get_memory_count(str(current_user.id))
    except Exception:
        pass

    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "total_sessions": total_sessions,
        "total_interactions": total_interactions,
        "total_memories": total_memories,
        "favorite_emotion": favorite_emotion,
        "emotion_breakdown": full_breakdown
    }

# ─────────────────────────────────────────────
# Global Endpoints / System Status
# ─────────────────────────────────────────────

@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "Emotion Robot v2.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0"}

# ─────────────────────────────────────────────
# Start Server
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Start the server
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
