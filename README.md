# EmoBot: Emotion-Aware Conversational Robot System

An end-to-end, multi-agent conversational robotic digital twin system. This project integrates real-time facial emotion recognition, an AI/RL-powered conversational backend, a ROS2-based command publisher, and an Unreal Engine 5 MetaHuman interface.

```
+--------------------+       +----------------------+       +-------------------------+
|                    |       |                      |       |                         |
|   React Frontend   |       |   FastAPI Backend    |       |   ROS2 Bridge Node      |
|   (Webcam / FER)   | ----> |   (AI/RL Logic)      | ----> |   (ROS2 Topic /speech)  |
|   Port: 5173       |       |   Port: 8001         |       |   Port: 8000 (WSL)      |
|                    |       |                      |       |                         |
+--------------------+       +----------------------+       +-------------------------+
                                                                         |
                                                                         v
                                                            +-------------------------+
                                                            |                         |
                                                            |   Unreal Engine 5       |
                                                            |   (MetaHuman/ConvAI)    |
                                                            |   input.json polling    |
                                                            |                         |
                                                            +-------------------------+
```

## System Architecture

1. **Frontend (React + Vite)**: Captures video streams from the webcam and runs real-time facial expression analysis using `fer` or `DeepFace` to detect user emotions.
2. **Backend (FastAPI)**: Serves as the central logic layer. It receives detected emotions, handles conversational state, filters out neutral states, enforces a 20-second cooldown per publish event, and triggers background dispatch tasks.
3. **ROS2 Bridge Node (`bridge.py`)**: Runs in a WSL (Ubuntu 22.04) environment with ROS2 Humble. It subscribes to `/speech` topics, tracks face morph targets (blend shapes), controls breathing/bob/sway animation offsets, and writes the speech text to `input.json`.
4. **Unreal Engine 5 Digital Twin**: Polls the shared local JSON file (`input.json`) to control lip sync, animation tracks, and conversational lines for a MetaHuman.

---

## Port Configurations

| Service | Technology | Port | Runs on |
| :--- | :--- | :--- | :--- |
| **Frontend** | React / Vite | `5173` | Windows |
| **Backend** | FastAPI / Python 3.13 | `8001` | Windows |
| **Bridge API** | FastAPI / ROS2 Humble | `8000` | WSL (Ubuntu 22.04) |

---

## Detailed Setup Instructions

### 1. Prerequisites
Ensure you have the following installed on your machine:
- **Windows 11 / 10**
- **Node.js** (v18 or higher)
- **Python 3.13** (Windows environment)
- **WSL 2** with **Ubuntu-22.04** installed
- **ROS2 Humble** (installed inside the WSL Ubuntu-22.04 distro)
- **Unreal Engine 5** (with MetaHuman and a ConvAI character scene)

---

### 2. Backend Installation (Windows)
1. Navigate to the backend directory:
   ```cmd
   cd backend
   ```
2. Create and activate a virtual environment (optional but recommended):
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install required packages:
   ```cmd
   pip install uvicorn fastapi tf-keras sentence-transformers chromadb fer mediapipe openai google-genai langchain langchain-community librosa
   ```
4. Create a `.env` file in the `backend/` directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
5. Start the backend server on port `8001`:
   ```cmd
   python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
   ```

---

### 3. Frontend Installation (Windows)
1. Navigate to the frontend directory:
   ```cmd
   cd frontend
   ```
2. Install the package dependencies:
   ```cmd
   npm install
   ```
3. Configure the backend connection in `src/config.ts`:
   ```typescript
   export const API_BASE_URL = 'http://localhost:8001';
   ```
4. Start the frontend developer server on port `5173`:
   ```cmd
   npm run dev
   ```

---

### 4. ROS2 Bridge Installation (WSL Ubuntu-22.04)
The bridge acts as the glue between the backend CLI commands and the Unreal Engine project file.

1. Open your WSL console targeting Ubuntu-22.04:
   ```cmd
   wsl -d Ubuntu-22.04
   ```
2. Source your ROS2 Humble environment:
   ```bash
   source /opt/ros/humble/setup.bash
   ```
3. Install FastAPI & Uvicorn in your WSL environment:
   ```bash
   pip3 install fastapi uvicorn
   ```
4. Run the bridge:
   ```bash
   python3 bridge.py
   ```
   *Note: The bridge will start an HTTP server on port `8000` and start a subscription to `/speech` and `/emotion` topics.*

---

## How to Run & Verify

1. **Start the WSL Bridge**:
   Ensure WSL is running and active on port `8000`.
2. **Start the Windows Backend**:
   Verify it runs on port `8001` (to prevent conflicts with the bridge).
3. **Start the Windows Frontend**:
   Open `http://localhost:5173` in your browser. Give webcam permissions.
4. **Trigger Actions**:
   - Smile or look sad at the camera.
   - The frontend will register the face, calculate the emotion, and POST to the backend.
   - The backend checks the 20-second cooldown and filters out `neutral` states.
   - If accepted, the backend launches a background process executing a ROS2 publish command inside WSL:
     ```bash
     wsl -d Ubuntu-22.04 -- bash -c "source /opt/ros/humble/setup.bash && ros2 topic pub -1 /speech std_msgs/msg/String \"{data: 'speaking:I am angry, I am very angry'}\""
     ```
   - The WSL Bridge receives this subscription, logs `Speaking...` and writes the message text to `/mnt/d/Unreal_Projects/Final_V2/input.json`.
   - Your Unreal Engine project reads the JSON to synchronize the MetaHuman's expressions and voice.
