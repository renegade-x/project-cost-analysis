import os

from dotenv import load_dotenv
from app import create_app

load_dotenv()
app = create_app(
    "app.config.ProductionConfig" if os.getenv("APP_ENV") == "production" else None
)
