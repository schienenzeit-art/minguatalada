import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from database.repositories.user_repository import UserRepository
import json

r = UserRepository()
user = r.get_by_username('admin')
print(json.dumps(user, default=str, ensure_ascii=False, indent=2))
