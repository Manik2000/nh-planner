import os
from pathlib import Path

BASE_URL = "https://www.kinonh.pl/"
PROGRAMME_URL = f"{BASE_URL}#repertuar@"
DB_PATH = Path(os.path.expanduser("~/.config/kinonh/kinonh.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
