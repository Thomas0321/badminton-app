import sqlite3
import os

def check_and_rebuild_db(db_path):
    need_rebuild = False
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(user)")
            cols = [row[1] for row in cur.fetchall()]
            required_fields = ['phone', 'preferred_region', 'notification_enabled', 'ban_until']
            missing_fields = [field for field in required_fields if field not in cols]
            if missing_fields:
                need_rebuild = True
            conn.close()
        except Exception as e:
            need_rebuild = True
    if need_rebuild:
        if os.path.exists(db_path):
            os.remove(db_path)
        print("[db_autofix] user 資料表缺少必要欄位，自動刪除並重建 badminton.db")
