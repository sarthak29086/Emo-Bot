# EmoBot Backend

The backend system is built on **FastAPI** (Python 3.13) and provides the logic core for handling emotion triggers, orchestrating LLM memory/actions, and communicating with the WSL ROS2 subsystem.

## Core Features

- **Emotion Routing**: Receives face analysis requests from the client.
- **ROS2 Publisher Integration**: Dispatches command-line shell triggers via WSL subprocess to publish ROS2 messages to `/speech`.
- **Ignore Neutral & Cooldown Logic**: Automatically filters out `neutral` expressions and throttles triggers, ensuring a minimum 20-second gap between consecutive speech events.
- **LLM Integrations**: Context graph, explainability module, and vector databases (ChromaDB) for conversation memory management.

---

## File Structure & Enhancements

- [main.py](file:///c:/Users/Sarthak%20Kardam/Documents/Coding/DL_Hackathon/Emotion-Aware-Conversational-Robot-System/backend/main.py): Runs on port `8001` to avoid conflict with the WSL bridge (running on port `8000`).
- [api/routes_emotion.py](file:///c:/Users/Sarthak%20Kardam/Documents/Coding/DL_Hackathon/Emotion-Aware-Conversational-Robot-System/backend/api/routes_emotion.py): Intercepts emotion states, runs rate limiting, and submits non-neutral events to the background task executor.
- [api/ros_publisher.py](file:///c:/Users/Sarthak%20Kardam/Documents/Coding/DL_Hackathon/Emotion-Aware-Conversational-Robot-System/backend/api/ros_publisher.py): Formulates standard ROS2 bash commands and executes them dynamically inside WSL:
  ```python
  subprocess.Popen(["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-c", cmd])
  ```
- [emotion_detection/face_emotion.py](file:///c:/Users/Sarthak%20Kardam/Documents/Coding/DL_Hackathon/Emotion-Aware-Conversational-Robot-System/backend/emotion_detection/face_emotion.py): Houses the `FER` facial emotion detector, patched to support `fer>=25.x` import paths seamlessly.

---

## Running the Backend

```cmd
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```
Once started, API documentation will be available at `http://localhost:8001/docs`.
