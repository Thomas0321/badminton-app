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
            if 'phone' not in cols:
                need_rebuild = True
            conn.close()
        except Exception as e:
            need_rebuild = True
    if need_rebuild:
        os.remove(db_path)
        print("[db_autofix] user 資料表缺少 phone 欄位，自動刪除並重建 badminton.db")
