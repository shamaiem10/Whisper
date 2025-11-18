# init_db.py
import sqlite3
from config import Config
import os

if not os.path.exists(Config.DATABASE):
    conn = sqlite3.connect(Config.DATABASE)
    c = conn.cursor()

    # Users table
    c.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
    ''')

    # Memories table
    c.execute('''
    CREATE TABLE memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        photo TEXT NOT NULL,
        location TEXT NOT NULL,
        feeling TEXT NOT NULL,
        mood TEXT,
        vibe TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')

    # Likes table
    c.execute('''
    CREATE TABLE likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        memory_id INTEGER NOT NULL,
        UNIQUE(user_id, memory_id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(memory_id) REFERENCES memories(id)
    )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully!")
else:
    print("Database already exists.")
