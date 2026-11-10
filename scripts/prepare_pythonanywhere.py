"""Prepare private production configuration in the cloned repository.

Run on PythonAnywhere: python -m scripts.prepare_pythonanywhere
This preserves existing secrets and never prints them.
"""
from pathlib import Path
import secrets
import shutil

from dotenv import dotenv_values, set_key


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env_file = root / ".env"
    if not env_file.exists():
        shutil.copyfile(root / ".env.example", env_file)
    values = dotenv_values(env_file)
    set_key(str(env_file), "APP_ENV", "production")
    if not values.get("SECRET_KEY"):
        set_key(str(env_file), "SECRET_KEY", secrets.token_hex(32))
    print("Production configuration prepared; existing secrets preserved.")
    print("Set the Web tab's virtualenv to the environment used for this command.")
    print("Copy deployment/pythonanywhere_wsgi.py into the linked WSGI configuration file.")
    print("Then reload the web app and open its HTTPS URL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
