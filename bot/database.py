import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path
        self._init()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init(self):
        with self._conn() as conn:
            cur = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id       INTEGER PRIMARY KEY,
                    username      TEXT,
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_vip        BOOLEAN   DEFAULT 0,
                    vip_expires_at TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       INTEGER,
                    download_date DATE,
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER,
                    days        INTEGER,
                    amount      INTEGER,
                    status      TEXT      DEFAULT 'pending',
                    donation_id TEXT,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            cur.execute("CREATE INDEX IF NOT EXISTS idx_dl_user_date ON downloads(user_id, download_date)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pay_status   ON payments(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_users_vip    ON users(is_vip, vip_expires_at)")

            # Migration: rename trakteer_id → donation_id if the old column still exists
            try:
                cur.execute("ALTER TABLE payments RENAME COLUMN trakteer_id TO donation_id")
                conn.commit()
                logger.info("DB migration: trakteer_id renamed to donation_id")
            except Exception:
                pass

            conn.commit()
            logger.info("Database berhasil diinisialisasi")

    # ── Users ──────────────────────────────────────────────────────────────────

    def register_user(self, user_id: int, username: str) -> None:
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO users (user_id, username, created_at)
                VALUES (?, ?, COALESCE(
                    (SELECT created_at FROM users WHERE user_id = ?),
                    CURRENT_TIMESTAMP
                ))
            """, (user_id, username, user_id))

    def is_user_vip(self, user_id: int) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT vip_expires_at FROM users WHERE user_id = ?", (user_id,)
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return False
            expires = datetime.fromisoformat(row[0])
            if expires <= datetime.now():
                conn.execute(
                    "UPDATE users SET is_vip = 0, vip_expires_at = NULL WHERE user_id = ?",
                    (user_id,)
                )
                return False
            return True

    def get_vip_status(self, user_id: int) -> Optional[Dict]:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT is_vip, vip_expires_at FROM users WHERE user_id = ?", (user_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            is_vip, expires_at = row
            if not is_vip or not expires_at:
                return {"is_active": False}
            expires = datetime.fromisoformat(expires_at)
            return {
                "is_active": expires > datetime.now(),
                "expires_at": expires_at,
                "expires_datetime": expires,
            }

    def activate_vip(self, user_id: int, expires_at: datetime) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, 'Unknown')",
                (user_id,)
            )
            conn.execute(
                "UPDATE users SET is_vip = 1, vip_expires_at = ? WHERE user_id = ?",
                (expires_at.isoformat(), user_id)
            )
        logger.info(f"VIP aktif untuk user {user_id} sampai {expires_at}")

    def remove_vip(self, user_id: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE users SET is_vip = 0, vip_expires_at = NULL WHERE user_id = ?",
                (user_id,)
            )
        logger.info(f"VIP dihapus untuk user {user_id}")

    def cleanup_expired_vip(self) -> None:
        with self._conn() as conn:
            cur = conn.execute("""
                UPDATE users
                SET is_vip = 0, vip_expires_at = NULL
                WHERE is_vip = 1 AND vip_expires_at <= CURRENT_TIMESTAMP
            """)
            if cur.rowcount:
                logger.info(f"Membersihkan {cur.rowcount} VIP yang kadaluarsa")

    def get_vip_users(self) -> List[Dict]:
        with self._conn() as conn:
            cur = conn.execute("""
                SELECT user_id, username, is_vip, vip_expires_at, created_at
                FROM users
                WHERE vip_expires_at IS NOT NULL
                  AND datetime(vip_expires_at) > datetime('now')
                ORDER BY vip_expires_at DESC
            """)
            rows = cur.fetchall()

        result = []
        for user_id, username, is_vip, expires_at, created_at in rows:
            expires = datetime.fromisoformat(expires_at)
            result.append({
                "user_id": user_id,
                "username": username,
                "is_vip": bool(is_vip),
                "vip_expires_at": expires_at,
                "created_at": created_at,
                "is_active": expires > datetime.now(),
                "expires_datetime": expires,
            })
        return result

    # ── Downloads ──────────────────────────────────────────────────────────────

    def get_daily_downloads(self, user_id: int) -> int:
        today = datetime.now().date()
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM downloads WHERE user_id = ? AND download_date = ?",
                (user_id, today)
            )
            return cur.fetchone()[0]

    def record_download(self, user_id: int) -> None:
        today = datetime.now().date()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO downloads (user_id, download_date) VALUES (?, ?)",
                (user_id, today)
            )

    # ── Payments ───────────────────────────────────────────────────────────────

    def record_payment(
        self,
        user_id: int,
        days: int,
        amount: int,
        status: str = "pending",
        donation_id: Optional[str] = None,
    ) -> int:
        with self._conn() as conn:
            if donation_id:
                cur = conn.execute(
                    "SELECT id FROM payments WHERE donation_id = ?", (donation_id,)
                )
                existing = cur.fetchone()
                if existing:
                    return existing[0]

            cur = conn.execute("""
                INSERT INTO payments (user_id, days, amount, status, donation_id)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, days, amount, status, donation_id))
            payment_id = cur.lastrowid
            logger.info(f"Payment dicatat: ID {payment_id}, user {user_id}, {days} hari, Rp{amount:,}")
            return payment_id

    def get_payment_by_id(self, payment_id: int) -> Optional[Dict]:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT id, user_id, days, amount, status, created_at, donation_id FROM payments WHERE id = ?",
                (payment_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return dict(zip(["id", "user_id", "days", "amount", "status", "created_at", "donation_id"], row))

    def update_payment_status(self, payment_id: int, status: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE payments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, payment_id)
            )

    # ── Stats ──────────────────────────────────────────────────────────────────

    def get_user_stats(self) -> Dict:
        with self._conn() as conn:
            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            vip_users = conn.execute(
                "SELECT COUNT(*) FROM users WHERE is_vip = 1 AND vip_expires_at > CURRENT_TIMESTAMP"
            ).fetchone()[0]
            today = datetime.now().date()
            downloads_today = conn.execute(
                "SELECT COUNT(*) FROM downloads WHERE download_date = ?", (today,)
            ).fetchone()[0]
            payment_rows = conn.execute(
                "SELECT status, COUNT(*) FROM payments GROUP BY status"
            ).fetchall()
            payment_stats = dict(payment_rows)

        return {
            "total_users": total_users,
            "vip_users": vip_users,
            "downloads_today": downloads_today,
            "payment_stats": payment_stats,
        }
