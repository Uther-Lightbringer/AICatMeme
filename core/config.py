import os
from dotenv import load_dotenv
load_dotenv()

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ak = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
LOG_CSV_FILE = os.path.join(ROOT_DIR, "user_submissions.csv")
EMOTION_FOLDER = os.path.join(ROOT_DIR, "meme")
BG_FOLDER = os.path.join(ROOT_DIR, "backgrounds")
OUTPUT_FOLDER = os.path.join(ROOT_DIR, "output")
FX_FOLDER = os.path.join(ROOT_DIR, "fx")
FONT_PATH = os.path.join(ROOT_DIR, "simhei.ttf")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
