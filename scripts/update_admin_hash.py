from pathlib import Path
import sys
sys.path.append(str(Path('.').resolve()))
from services.password_service import PasswordService
from database.db import get_connection

h = PasswordService.hash_password('admin123')
with get_connection() as conn:
    conn.execute("UPDATE users SET password_hash=?, is_active=1, failed_attempts=0, locked_until=NULL WHERE username='admin'", (h,))
    conn.commit()
print('updated admin hash')
