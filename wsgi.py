from dotenv import load_dotenv
from app import create_app
from config import Config

load_dotenv()
app = create_app(Config)