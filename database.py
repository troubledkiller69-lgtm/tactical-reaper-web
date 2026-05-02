import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Union, Optional, Tuple, Any

logger = logging.getLogger(__name__)

DB_NAME = "eni_reper.db"


class DatabaseManager:
    def __init__(self) -> None:
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self._lock = threading.Lock()
        self._create_tables()

    def _create_tables(self) -> None:
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS keys (
                                key TEXT PRIMARY KEY,
                                duration_hours INTEGER,
                                status TEXT DEFAULT 'active'
                              )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                tg_id INTEGER PRIMARY KEY,
                                expiry TIMESTAMP,
                                key_used TEXT
                              )''')
            self.conn.commit()

    def generate_key(self, hours: int = 24) -> str:
        new_key = f"Retri-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO keys (key, duration_hours) VALUES (?, ?)", (new_key, hours))
            self.conn.commit()
        logger.info("Generated key %s (%dh)", new_key, hours)
        return new_key

    def redeem_key(self, tg_id: int, key_str: str) -> Tuple[bool, str]:
        with self._lock:
            try:
                with self.conn:
                    cursor = self.conn.cursor()
                    cursor.execute(
                        "SELECT duration_hours FROM keys WHERE key = ? AND status = 'active'",
                        (key_str,),
                    )
                    row = cursor.fetchone()

                    if not row:
                        return False, "Invalid or already redeemed key."

                    duration_hours = row[0]

                    cursor.execute("SELECT expiry FROM users WHERE tg_id = ?", (tg_id,))
                    user_row = cursor.fetchone()

                    now = datetime.now()
                    if user_row:
                        current_expiry = datetime.strptime(user_row[0], "%Y-%m-%d %H:%M:%S")
                        new_expiry = max(current_expiry, now) + timedelta(hours=duration_hours)
                        cursor.execute(
                            "UPDATE users SET expiry = ?, key_used = ? WHERE tg_id = ?",
                            (new_expiry.strftime("%Y-%m-%d %H:%M:%S"), key_str, tg_id),
                        )
                    else:
                        new_expiry = now + timedelta(hours=duration_hours)
                        cursor.execute(
                            "INSERT INTO users (tg_id, expiry, key_used) VALUES (?, ?, ?)",
                            (tg_id, new_expiry.strftime("%Y-%m-%d %H:%M:%S"), key_str),
                        )

                    cursor.execute("UPDATE keys SET status = 'redeemed' WHERE key = ?", (key_str,))

                logger.info("Key %s redeemed by user %d, expires %s", key_str, tg_id, new_expiry)
                return True, new_expiry.strftime("%Y-%m-%d %H:%M:%S")
            except sqlite3.Error as e:
                logger.error("Database error during key redemption: %s", e)
                return False, f"Database error: {e}"

    def check_license(self, tg_id: int) -> Tuple[bool, Optional[str]]:
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT expiry FROM users WHERE tg_id = ?", (tg_id,))
            row = cursor.fetchone()

        if not row:
            return False, None

        expiry = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        if datetime.now() > expiry:
            return False, row[0]

        return True, row[0]

    def get_stats(self) -> Tuple[int, int]:
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM keys WHERE status = 'active'")
            active_keys = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users")
            active_users = cursor.fetchone()[0]
        return active_keys, active_users
