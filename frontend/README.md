# EmoBot Frontend Client

This is the front-end user interface for the **EmoBot Digital Twin** project. It handles real-time video capture, facial expressions analysis, and lists the detected emotions.

## Core Features

- **Real-Time Webcam Streaming**: Captures local camera stream inside the browser safely.
- **Emotion Recognition Dispatch**: Integrates with the backend API to periodically check and transmit the user's current facial expressions.
- **Configurable API Endpoint**: Communicates with the FastAPI backend through [src/config.ts](file:///c:/Users/Sarthak%20Kardam/Documents/Coding/DL_Hackathon/Emotion-Aware-Conversational-Robot-System/frontend/src/config.ts) set to port `8001`.

---

## Technical Stack

- **Framework**: React 18+ (Vite)
- **Language**: TypeScript
- **Styling**: TailwindCSS & Custom CSS
- **HTTP Client**: Axios / Fetch

---

## Setup & Running

1. **Install dependencies**:
   ```cmd
   npm install
   ```

2. **Verify configuration**:
   Open [src/config.ts](file:///c:/Users/Sarthak%20Kardam/Documents/Coding/DL_Hackathon/Emotion-Aware-Conversational-Robot-System/frontend/src/config.ts) and verify the endpoint points to your backend instance:
   ```typescript
   export const API_BASE_URL = 'http://localhost:8001';
   ```

3. **Start the dev server**:
   ```cmd
   npm run dev
   ```
   Open `http://localhost:5173` in your browser to interact with the interface.

