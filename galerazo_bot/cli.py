import argparse

from .commands import handle_text
from .config import load_settings
from .database import Database
from .roles import UserLevel


def main() -> None:
    parser = argparse.ArgumentParser(description="Probar Galerazo Bot localmente.")
    parser.add_argument("message", nargs="+", help="Mensaje a procesar, por ejemplo: hola")
    args = parser.parse_args()

    settings = load_settings()
    db = Database(settings.database_path)
    text = " ".join(args.message)

    response = handle_text(text, sender_id="local-cli", db=db, user_level=UserLevel.DEV)
    print(response)


if __name__ == "__main__":
    main()
