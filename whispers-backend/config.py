from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    SECRET_KEY = "shamaiem"
    DATABASE = "database.db"
    UPLOAD_FOLDER = "uploads"
    HF_API_KEY = os.getenv("HF_API_KEY")
