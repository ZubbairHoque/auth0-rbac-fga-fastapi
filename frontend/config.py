import os
from dotenv import load_dotenv


load_dotenv(dotenv_path="frontend/.env")

# Reusable configuration
BACKEND_URL = os.getenv("backend_url", "http://localhost:8000")