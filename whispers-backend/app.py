import os
import requests
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

# Initialize Flask
app = Flask(__name__)
app.config.from_object(Config)
CORS(app, supports_credentials=True)
jwt = JWTManager(app)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# DB helper
def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ==========================
# AI INSIGHT WITH QWEN
# ==========================
HF_API_KEY = os.getenv("HF_TOKEN") or Config.HF_API_KEY
HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL = "Qwen/Qwen3-Coder-480B-A35B-Instruct:novita"

def analyze_text_with_ai(location, feeling):
    prompt = f"Location: {location}\nFeeling: {feeling}\nProvide a 2-3 line emotional travel insight."
    payload = {
        "model": HF_MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print("AI Error:", e)
        return "AI insight could not be generated."

@app.route('/ai-insight', methods=['POST'])
@jwt_required()
def ai_insight():
    data = request.get_json()
    location = data.get("location")
    feeling = data.get("feeling")
    if not location or not feeling:
        return jsonify({"error": "Location and feeling are required"}), 400
    insight = analyze_text_with_ai(location, feeling)
    return jsonify({"insight": insight})

# ==========================
# AUTH ROUTES
# ==========================
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    hashed_password = generate_password_hash(password)
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                  (username, email, hashed_password))
        conn.commit()
        conn.close()
        return jsonify({"message": "User created successfully!"}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Username or email already exists"}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    if user and check_password_hash(user["password"], password):
        access_token = create_access_token(identity=str(user["id"]))
        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "username": user["username"]
        })
    else:
        return jsonify({"error": "Invalid email or password"}), 401

# ==========================
# MEMORY ROUTE
# ==========================
@app.route('/memory', methods=['POST'])
@jwt_required()
def upload_memory():
    user_id = int(get_jwt_identity())
    location = request.form.get('location')
    feeling = request.form.get('feeling')
    mood = request.form.get('mood', 'happy')
    vibe = request.form.get('vibe', 'nature')
    file = request.files.get('photo')
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Photo is required and must be an image file"}), 400
    if not location or not feeling:
        return jsonify({"error": "Location and feeling are required"}), 400

    filename = secure_filename(file.filename)
    file.save(os.path.join(Config.UPLOAD_FOLDER, filename))

    try:
        insight = analyze_text_with_ai(location, feeling)
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO memories (user_id, photo, location, feeling, mood, vibe)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, filename, location, feeling, mood, vibe))
        conn.commit()
        conn.close()
        return jsonify({"message": "Memory uploaded successfully!", "ai_insight": insight}), 201
    except Exception as e:
        print("DB Error:", e)
        return jsonify({"error": "Failed to insert memory", "exception": str(e)}), 500

# ==========================
# FEED, LIKE, DASHBOARD ROUTES
# ==========================
@app.route('/feed', methods=['GET'])
@jwt_required()
def feed():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT m.id, m.photo, m.location, m.feeling, m.mood, m.vibe, u.username,
               (SELECT COUNT(*) FROM likes WHERE memory_id = m.id) as like_count
        FROM memories m
        JOIN users u ON m.user_id = u.id
        ORDER BY m.created_at DESC
    """)
    memories = [dict(row) for row in c.fetchall()]
    conn.close()
    for mem in memories:
        mem['photo_url'] = f"/uploads/{mem['photo']}"
    return jsonify(memories)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename)

@app.route('/like/<int:memory_id>', methods=['POST'])
@jwt_required()
def like_memory(memory_id):
    user_id = int(get_jwt_identity())
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM likes WHERE user_id = ? AND memory_id = ?", (user_id, memory_id))
    existing = c.fetchone()
    if existing:
        c.execute("DELETE FROM likes WHERE id = ?", (existing["id"],))
        conn.commit()
        conn.close()
        return jsonify({"message": "Unliked successfully"})
    else:
        c.execute("INSERT INTO likes (user_id, memory_id) VALUES (?, ?)", (user_id, memory_id))
        conn.commit()
        conn.close()
        return jsonify({"message": "Liked successfully"})

@app.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    user_id = int(get_jwt_identity())
    conn = get_db_connection()
    c = conn.cursor()

    # Get user info and memories
    c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()

    c.execute("SELECT location, feeling, mood, vibe FROM memories WHERE user_id = ?", (user_id,))
    memories = c.fetchall()

    # Prepare AI prompt based on user's memories
    memories_summary = "\n".join(
        [f"{m['location']} - Feeling: {m['feeling']}, Mood: {m['mood']}, Vibe: {m['vibe']}" for m in memories]
    )

    # Improved prompt
    prompt = f"""
    You are a travel AI assistant. A user has shared the following travel memories:
    {memories_summary}

    Based on these experiences, suggest 3 new travel destinations the user might enjoy. 
    For each destination, provide detailed information including:
    - Place name
    - Area/Region
    - Why this place suits the user's travel personality and emotional vibes
    - Unique cultural or local specialties (food, activities, landmarks, festivals, etc.)
    - One fun activity or experience the user should not miss
    - A placeholder image URL if you don't know an exact image

    Respond ONLY in JSON format as an array, like this:

    [
      {{
        "place": "Beautiful Place Name",
        "area": "Region or City",
        "reason": "Why this place is perfect for the user",
        "specialties": "Local food, activities, landmarks, culture",
        "fun_activity": "A fun thing to do here",
        "image_url": "https://via.placeholder.com/400x300?text=Place+Name"
      }}
    ]
    """

    payload = {
        "model": HF_MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }

    recommendations = []
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        raw_content = data["choices"][0]["message"]["content"].strip()
        import json
        recommendations = json.loads(raw_content)
    except Exception as e:
        print("AI Error:", e)
        # Fallback recommendations
        recommendations = [
            {
                "place": "Hunza Valley",
                "area": "Gilgit-Baltistan",
                "reason": "Peaceful mountains, perfect for reflective and scenic travel",
                "specialties": "Local apricots, traditional Hunza cuisine, majestic mountain views",
                "fun_activity": "Trekking to Ultar Sar or exploring Baltit Fort",
                "image_url": "https://via.placeholder.com/400x300?text=Hunza+Valley"
            },
            {
                "place": "Skardu",
                "area": "Gilgit-Baltistan",
                "reason": "Ideal for nature lovers and those who enjoy calm, serene landscapes",
                "specialties": "Deosai National Park, Skardu bazaar, trout fishing",
                "fun_activity": "Visit Shangrila Resort and take a boat ride on Upper Kachura Lake",
                "image_url": "https://via.placeholder.com/400x300?text=Skardu"
            },
            {
                "place": "Lahore Food Streets",
                "area": "Punjab",
                "reason": "Perfect for food enthusiasts and cultural explorers",
                "specialties": "Street food like golgappa, nihari, and sweets; historic architecture",
                "fun_activity": "Walk along Fort Road Food Street and try local delicacies",
                "image_url": "https://via.placeholder.com/400x300?text=Lahore+Food+Streets"
            }
        ]

    conn.close()
    return jsonify({
        "username": user["username"],
        "recommendations": recommendations
    })

@app.route('/dashboard-full', methods=['GET'])
@jwt_required()
def dashboard_full():
    user_id = int(get_jwt_identity())
    conn = get_db_connection()
    c = conn.cursor()

    # 1️⃣ User info
    c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()

    # 2️⃣ Only logged-in user's memories
    c.execute("SELECT location, feeling, mood, vibe, photo, created_at FROM memories WHERE user_id = ?", (user_id,))
    memories_raw = c.fetchall()

    memories = [
        {
            "location": m["location"],
            "feeling": m["feeling"],
            "mood": m["mood"],
            "vibe": m["vibe"],
            "date": m["created_at"],
            "image_url": f"/uploads/{m['photo']}"  # Only filename, served by Flask
        }
        for m in memories_raw
    ]

    total_memories = len(memories)

    # 3️⃣ Likes count
    c.execute("""
        SELECT COUNT(*) as total_likes
        FROM likes l
        JOIN memories m ON l.memory_id = m.id
        WHERE m.user_id = ?
    """, (user_id,))
    total_likes = c.fetchone()["total_likes"]

    # 4️⃣ AI personality + vibes + moods
    memories_summary = "\n".join(
        [f"{m['location']} - Feeling: {m['feeling']}, Mood: {m['mood']}, Vibe: {m['vibe']}" for m in memories]
    )

    prompt = f"""
    Analyze the travel memories of the user:
    {memories_summary}

    1. Give a travel personality type and short description.
    2. Give top 3 vibes (like adventurous, calm, cultural etc.).
    3. Give top 3 moods with percentage distribution.

    Respond ONLY in JSON format like:
    {{
        "personality": {{
            "type": "...",
            "description": "...",
            "topVibes": ["...", "...", "..."]
        }},
        "topMoods": [
            {{"mood": "...", "percentage": 40}},
            {{"mood": "...", "percentage": 35}},
            {{"mood": "...", "percentage": 25}}
        ]
    }}
    """

    payload = {"model": HF_MODEL, "messages": [{"role": "user", "content": prompt}]}
    headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"}

    try:
        import json
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        ai_data = response.json()
        raw_content = ai_data["choices"][0]["message"]["content"].strip()
        ai_result = json.loads(raw_content)
    except Exception as e:
        print("AI Error:", e)
        ai_result = {
            "personality": {"type": "Traveler", "description": "You love exploring.", "topVibes": ["Adventurous", "Curious", "Relaxed"]},
            "topMoods": [{"mood": "Happy", "percentage": 50}, {"mood": "Excited", "percentage": 30}, {"mood": "Calm", "percentage": 20}]
        }

    conn.close()

    return jsonify({
        "username": user["username"],
        "total_memories": total_memories,
        "total_likes": total_likes,
        "memories": memories,           # Only logged-in user's memories
        "personality": ai_result["personality"],
        "topMoods": ai_result["topMoods"]
    })


# ==========================
# RUN APP
# ==========================
if __name__ == '__main__':
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
