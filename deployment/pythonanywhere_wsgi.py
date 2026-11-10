"""Copy this into the WSGI configuration file linked on PythonAnywhere's Web tab.

Clone the repository into ~/project-cost-analysis and configure its ignored .env
before reloading the web app. Choose the same Python version as its virtualenv.
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

project_root = Path.home() / "project-cost-analysis"
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")

from wsgi import app as application  # noqa: E402
