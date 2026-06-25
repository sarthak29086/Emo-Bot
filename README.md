# EmoBot: Emotion-Aware Conversational Robot System

EmoBot is an end-to-end, multi-agent conversational robotic digital twin system designed to create empathetic, responsive virtual agents. It captures human facial emotional states in real-time and translates them into interactive conversational actions and behaviors on a high-fidelity Unreal Engine 5 MetaHuman.

---

## 💡 About the Project

### What is this project about?
Modern conversational AI often lacks situational context and emotional empathy. This project builds a real-time reactive bridge between a user's physical emotional expressions (captured via webcam) and a digital twin's responses. When a user looks angry, sad, or happy, the digital twin detects this transition, adapts its internal state, and speaks with context-appropriate responses, creating a highly realistic human-to-digital-twin conversational loop.

### What we did
We designed and implemented a full data and execution pipeline spanning web development, deep learning, robotic middlewares, and gaming engine animations:
1. Built a camera-based real-time **facial expression detector** on a web client.
2. Constructed a central **orchestration backend** to manage state, filter idle inputs, and coordinate message dispatches.
3. Configured an interactive **WSL2-to-Windows communication bridge** using ROS2 message passing.
4. Programmed a **dynamic file polling watcher** inside Unreal Engine 5 to drive voice lip-sync and narrative animations on a MetaHuman.

### How we did it
We integrated a stack of modern, cross-platform technologies:
* **Real-Time Classification**: Used standard cameras and **Facial Emotion Recognition (FER)** deep learning models in a React web client to stream emotion frames.
* **API Orchestration**: Engineered a **FastAPI** server on Windows to filter emotions and manage event cycles (with a 20-second cooldown per event).
* **Robotics Middleware**: Utilized **ROS2 Humble** running in a WSL2 Ubuntu environment. The backend dispatches interactive ROS2 commands directly, which are processed by a dedicated **ROS2 Bridge subscription node**.
* **Engine Integration & AI Speech**: Configured **Unreal Engine 5** with the **VaRest** JSON utility to read bridge events, and integrated **ConvAI** to drive the MetaHuman's natural language responses and visual lipsyncing dynamically.

---


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

---

## 📂 Project Structure

```
.
├── backend/                    # FastAPI backend server
│   ├── api/                    # API endpoints & ROS2 commands dispatcher
│   │   ├── ros_publisher.py    # Spawns interactive WSL shells to publish ROS2 messages
│   │   └── routes_emotion.py   # Cooldown filter & dispatch router
│   ├── emotion_detection/      # Face detection and emotion classification
│   │   └── face_emotion.py     # Webcam FER image processor
│   ├── main.py                 # FastAPI backend entrypoint (port 8001)
│   └── README.md               # Backend installation details
│
├── frontend/                   # React (TypeScript) + Vite user interface
│   ├── src/                    # App, components, and API client configs
│   │   └── config.ts           # Endpoint configs (points to port 8001)
│   └── README.md               # Frontend installation details
│
├── unreal/                     # Unreal Engine 5 digital twin documentation
│   ├── blueprints/             # Copy-pasteable blueprint graphs
│   │   └── json_watcher_nodes.txt  # Event Graph text for BP_Natalia
│   └── README.md               # Required plugins and blueprint details
│
├── bridge.py                   # WSL ROS2 subscriber -> Windows input.json bridge (port 8000)
├── .gitattributes              # Git LFS rules for large binary tracking
├── .gitignore                  # Build cache and virtual environment ignore files
└── README.md                   # Main project setup and runner guide (this file)
```

---

## ⚡ System Architecture & Flow

1. **Frontend (React + Vite)**: Captures webcam video streams and processes real-time facial expressions using `fer` to classify emotions.
2. **Backend (FastAPI)**: Serves as the logic center. It filters out `neutral` states, enforces a **20-second cooldown** to prevent spamming, and dispatches background tasks to trigger ROS2 publishers inside WSL.
3. **ROS2 Bridge Node (`bridge.py`)**: Runs in the WSL2 Ubuntu container (ROS2 Humble). It subscribes to `/speech`, extracts conversational commands, and writes them to a shared file (`input.json`) on the Windows filesystem.
4. **Unreal Engine 5 Digital Twin**: Polls the shared local JSON file (`input.json`) via a timer, triggers MetaHuman voice responses using **ConvAI**, and animates lips and gestures dynamically.

---

## 🔌 Port Configurations

| Service | Technology | Port | Runs on |
| :--- | :--- | :--- | :--- |
| **Frontend UI** | React / Vite | `5173` | Windows |
| **Backend API** | FastAPI / Python 3.13 | `8001` | Windows |
| **WSL ROS2 Bridge** | FastAPI / ROS2 Humble | `8000` | WSL2 (Ubuntu 22.04) |

---

## 🛠️ Step-by-Step Installation

### 1. Prerequisites
Ensure you have the following installed on your host system:
* **Windows 11 / 10**
* **Node.js** (v18 or higher)
* **Python 3.13** (Windows environment)
* **WSL 2** with **Ubuntu-22.04**
* **ROS2 Humble** (installed inside the WSL Ubuntu distro)
* **Unreal Engine 5** (with **VaRest** and **ConvAI** plugins)

---

### 2. Backend Setup (Windows)
1. Navigate to the backend directory:
   ```cmd
   cd backend
   ```
2. Create and activate a virtual environment:
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```cmd
   pip install uvicorn fastapi tf-keras sentence-transformers chromadb fer mediapipe openai google-genai langchain langchain-community librosa
   ```
4. Create a `.env` file in the `backend/` directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

---

### 3. Frontend Setup (Windows)
1. Navigate to the frontend directory:
   ```cmd
   cd frontend
   ```
2. Install package dependencies:
   ```cmd
   npm install
   ```

---

### 4. ROS2 Bridge Setup (WSL Ubuntu)
1. Open your WSL console targeting Ubuntu-22.04:
   ```cmd
   wsl -d Ubuntu-22.04
   ```
2. Install FastAPI and Uvicorn in your WSL environment:
   ```bash
   pip3 install fastapi uvicorn
   ```

---

## 🚀 How to Run & Operate the System

To get the full system working, start the services in the following order:

### Step 1: Start the ROS2 Bridge (WSL Terminal)
Open WSL and run the bridge. This listens for ROS2 messages and outputs `input.json` to Windows.
```bash
wsl -d Ubuntu-22.04
source /opt/ros/humble/setup.bash
# Run the bridge from your project root folder
python3 bridge.py
```
*(The bridge starts an HTTP server on port `8000` and creates a subscription to the `/speech` topic).*

### Step 2: Start the Backend (Windows Command Prompt)
Open a Windows command prompt, navigate to `backend/`, and start the FastAPI server:
```cmd
cd backend
.venv\Scripts\activate
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Step 3: Start the Frontend (Windows Command Prompt)
Open a new Windows command prompt, navigate to `frontend/`, and launch the web interface:
```cmd
cd frontend
npm run dev
```
Open `http://localhost:5173` in your browser and grant webcam permissions.

### Step 4: Play the Unreal Engine Scene
1. Open your Unreal Engine project (configured with **BP_Natalia**).
2. Ensure the Natalia Character Blueprint includes the Event Graph logic parsing the JSON file from:
   `D:/Unreal_Projects/Final_V2/input.json`
   *(Refer to [unreal/README.md](unreal/README.md) to copy-paste the blueprint graph nodes).*
3. Press **Play** in the Unreal Editor.

### Step 5: Verify End-to-End Operation
* Smile or look sad at your webcam in the React frontend.
* The frontend detects the face and sends it to the Windows backend.
* The backend executes a WSL background publisher command using an interactive shell (`bash -i -c`):
  ```bash
  wsl -d Ubuntu-22.04 -- bash -i -c "source /opt/ros/humble/setup.bash && ros2 topic pub -1 /speech std_msgs/msg/String \"{data: 'speaking:I am angry, very angry, absolutely furious'}\""
  ```
* The bridge picks up the `/speech` message, logs `Speaking...` and writes the message text to `D:/Unreal_Projects/Final_V2/input.json`.
* The Unreal Engine character detects the file change, plays lip-sync voice dialogue via ConvAI, and moves!

---

## 💾 Versioning the Unreal Engine Project
This repository is configured to version the Unreal project **blueprints and config settings** without the heavy 1.5GB binary assets.
* See [unreal/README.md](unreal/README.md) for how to use Git LFS or push level configurations.
* See [unreal/blueprints/json_watcher_nodes.txt](unreal/blueprints/json_watcher_nodes.txt) for copy-pasteable blueprint graphs.

*Built with ❤️ by the EmoDynamics team during the HCL Hack60 Hackathon.*