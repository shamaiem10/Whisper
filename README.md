# Whisper

Whisper is an AI-powered travel memory tracker and recommendation system. It allows users to log their travel experiences, track emotions and vibes, and get AI-generated insights and suggestions for new travel destinations.

---

## Features

- **User Authentication**: Sign up and log in securely using JWT tokens.
- **Memory Upload**: Add travel memories with location, feeling, mood, vibe, and a photo.
- **AI Insights**: Get emotional travel insights and suggestions for new destinations using AI.
- **Memory Feed**: Explore memories shared by yourself or others, with like functionality.
- **Personality Dashboard**: Visualize your travel personality, top vibes, and emotional distribution.

---

## Project Structure

The project is split into two repositories:

1. **Backend & Full Project (This Repo)**: Handles the Flask backend, database, AI integration, and APIs.
2. **Frontend (React)**: The frontend is hosted in a separate repository: [Whisper Frontend](https://github.com/shamaiem10/whisper-frontend).

You can clone the frontend repo separately to run the full application.

---

## Installation & Setup

### Backend

1. Clone this repository:

```bash
git clone https://github.com/shamaiem10/Whisper.git
cd Whisper
```

2. Create a virtual environment and install dependencies:

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```
3. Set up environment variables (example .env):


```bash
HF_API_KEY=your_huggingface_api_key
SECRET_KEY=your_jwt_secret
DATABASE=whisper.db
UPLOAD_FOLDER=uploads
```

4. Run the Flask backend:

```bash

python app.py
```
5. Frontend
The frontend is in a separate repo: Whisper Frontend. Clone it and run:

```bash

npm install
npm run dev
```
