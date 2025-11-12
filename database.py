import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_vip BOOLEAN DEFAULT 0,
                    vip_expires_at TIMESTAMP
                )
            """)
            
            # Downloads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    download_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Payments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    days INTEGER,
                    amount INTEGER,
                    status TEXT DEFAULT 'pending',
                    trakteer_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloads_user_date ON downloads(user_id, download_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_vip ON users(is_vip, vip_expires_at)")
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def register_user(self, user_id: int, username: str) -> None:
        """Register or update user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO users (user_id, username, created_at)
                VALUES (?, ?, COALESCE((SELECT created_at FROM users WHERE user_id = ?), CURRENT_TIMESTAMP))
            """, (user_id, username, user_id))
            conn.commit()
    
    def is_user_vip(self, user_id: int) -> bool:
        """Check if user has active VIP"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT vip_expires_at FROM users 
                WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            if not result or not result[0]:
                return False
                
            expires_at = result[0]
            
            # Check if VIP is still valid
            expires_datetime = datetime.fromisoformat(expires_at)
            if expires_datetime <= datetime.now():
                # Expire VIP
                cursor.execute("""
                    UPDATE users SET is_vip = 0, vip_expires_at = NULL 
                    WHERE user_id = ?
                """, (user_id,))
                conn.commit()
                return False
                
            return True
    
    def get_vip_status(self, user_id: int) -> Optional[Dict]:
        """Get detailed VIP status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT is_vip, vip_expires_at FROM users 
                WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
                
            is_vip, expires_at = result
            if not is_vip or not expires_at:
                return {"is_active": False}
                
            expires_datetime = datetime.fromisoformat(expires_at)
            is_active = expires_datetime > datetime.now()
            
            return {
                "is_active": is_active,
                "expires_at": expires_at,
                "expires_datetime": expires_datetime
            }
    
    def activate_vip(self, user_id: int, expires_at: datetime) -> None:
        """Activate VIP for user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Ensure user exists first
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_id, username) 
                VALUES (?, 'Unknown')
            """, (user_id,))
            
            # Now update VIP status
            cursor.execute("""
                UPDATE users 
                SET is_vip = 1, vip_expires_at = ?
                WHERE user_id = ?
            """, (expires_at.isoformat(), user_id))
            
            # Verify the update worked
            cursor.execute("""
                SELECT vip_expires_at FROM users WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()
            
            conn.commit()
            logger.info(f"VIP activated for user {user_id} until {expires_at}, verified: {result}")
    
    def get_daily_downloads(self, user_id: int) -> int:
        """Get user's downloads count for today"""
        today = datetime.now().date()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM downloads 
                WHERE user_id = ? AND download_date = ?
            """, (user_id, today))
            
            return cursor.fetchone()[0]
    
    def record_download(self, user_id: int) -> None:
        """Record a download"""
        today = datetime.now().date()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO downloads (user_id, download_date)
                VALUES (?, ?)
            """, (user_id, today))
            conn.commit()
    
    def record_payment(self, user_id: int, days: int, amount: int, status: str = "pending", trakteer_id: str = None) -> int:
        """Record a payment with better duplicate prevention"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if payment with same trakteer_id already exists
            if trakteer_id:
                cursor.execute('SELECT id, status FROM payments WHERE trakteer_id = ?', (trakteer_id,))
                existing = cursor.fetchone()
                if existing:
                    logger.info(f"Payment with Trakteer ID {trakteer_id} already exists with status: {existing[1]}")
                    return existing[0]
            
            # Additional check for potential duplicates (same user, amount, days within last hour)
            cursor.execute("""
                SELECT id FROM payments 
                WHERE user_id = ? AND days = ? AND amount = ? 
                AND datetime(created_at) > datetime('now', '-1 hour')
                AND status = 'pending'
            """, (user_id, days, amount))
            
            recent_duplicate = cursor.fetchone()
            if recent_duplicate:
                logger.warning(f"Potential duplicate payment detected for user {user_id}, using existing ID {recent_duplicate[0]}")
                return recent_duplicate[0]
            
            cursor.execute("""
                INSERT INTO payments (user_id, days, amount, status, trakteer_id)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, days, amount, status, trakteer_id))
            conn.commit()
            
            payment_id = cursor.lastrowid
            logger.info(f"Recorded NEW payment: ID {payment_id}, User {user_id}, {days} days, {amount}, Status: {status}")
            return payment_id
    
    def get_pending_payments(self) -> List[Dict]:
        """Get all pending payments"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, days, amount, created_at, trakteer_id
                FROM payments 
                WHERE status = 'pending'
                ORDER BY created_at ASC
            """)
            
            results = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "days": row[2],
                    "amount": row[3],
                    "created_at": row[4],
                    "trakteer_id": row[5]
                }
                for row in results
            ]
    
    def get_payment_by_trakteer_id(self, trakteer_id: str) -> Optional[Dict]:
        """Get payment by Trakteer ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, days, amount, status, created_at, trakteer_id
                FROM payments 
                WHERE trakteer_id = ?
            """, (trakteer_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
                
            return {
                "id": result[0],
                "user_id": result[1],
                "days": result[2],
                "amount": result[3],
                "status": result[4],
                "created_at": result[5],
                "trakteer_id": result[6]
            }

    def get_payment_by_characteristics(self, user_id: int, amount: int, days: int) -> Optional[Dict]:
        """Get payment by user characteristics - prevent duplicates even after VIP removal"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, days, amount, status, created_at, trakteer_id
                FROM payments 
                WHERE user_id = ? AND amount = ? AND days = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (user_id, amount, days))
            
            result = cursor.fetchone()
            if not result:
                return None
                
            return {
                "id": result[0],
                "user_id": result[1],
                "days": result[2],
                "amount": result[3],
                "status": result[4],
                "created_at": result[5],
                "trakteer_id": result[6]
            }

    def has_processed_payment_combination(self, user_id: int, amount: int, days: int) -> bool:
        """Check if user ever had any payment processed for this amount/days combination"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM payments 
                WHERE user_id = ? AND amount = ? AND days = ? 
                AND status IN ('approved', 'rejected', 'expired')
            """, (user_id, amount, days))
            
            count = cursor.fetchone()[0]
            return count > 0

    def get_payment_by_id(self, payment_id: int) -> Optional[Dict]:
        """Get payment by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, days, amount, status, created_at, trakteer_id
                FROM payments 
                WHERE id = ?
            """, (payment_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
                
            return {
                "id": result[0],
                "user_id": result[1],
                "days": result[2],
                "amount": result[3],
                "status": result[4],
                "created_at": result[5],
                "trakteer_id": result[6]
            }
    
    def update_payment_status(self, payment_id: int, status: str) -> None:
        """Update payment status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE payments 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, payment_id))
            conn.commit()
    
    def cleanup_expired_vip(self) -> None:
        """Clean up expired VIP users"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET is_vip = 0, vip_expires_at = NULL
                WHERE is_vip = 1 AND vip_expires_at <= CURRENT_TIMESTAMP
            """)
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Cleaned up {cursor.rowcount} expired VIP users")
    
    def get_vip_users(self) -> List[Dict]:
        """Get all VIP users with their status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, is_vip, vip_expires_at, created_at
                FROM users 
                WHERE vip_expires_at IS NOT NULL 
                AND datetime(vip_expires_at) > datetime('now')
                ORDER BY vip_expires_at DESC
            """)
            
            results = cursor.fetchall()
            vip_users = []
            
            for row in results:
                user_id, username, is_vip, vip_expires_at, created_at = row
                
                # Check if VIP is still active
                expires_datetime = datetime.fromisoformat(vip_expires_at)
                is_active = expires_datetime > datetime.now()
                
                vip_users.append({
                    "user_id": user_id,
                    "username": username,
                    "is_vip": bool(is_vip),
                    "vip_expires_at": vip_expires_at,
                    "created_at": created_at,
                    "is_active": is_active,
                    "expires_datetime": expires_datetime
                })
            
            return vip_users
    
    def remove_vip(self, user_id: int) -> None:
        """Remove VIP status from user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET is_vip = 0, vip_expires_at = NULL
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()
            logger.info(f"VIP status removed for user {user_id}")

    def get_user_stats(self) -> Dict:
        """Get overall user statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total users
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            # Active VIP users
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE is_vip = 1 AND vip_expires_at > CURRENT_TIMESTAMP
            """)
            vip_users = cursor.fetchone()[0]
            
            # Total downloads today
            today = datetime.now().date()
            cursor.execute("""
                SELECT COUNT(*) FROM downloads 
                WHERE download_date = ?
            """, (today,))
            downloads_today = cursor.fetchone()[0]
            
            # Total payments by status
            cursor.execute("SELECT status, COUNT(*) FROM payments GROUP BY status")
            payment_stats = dict(cursor.fetchall())
            
            return {
                "total_users": total_users,
                "vip_users": vip_users,
                "downloads_today": downloads_today,
                "payment_stats": payment_stats,
                "total_approved_payments": payment_stats.get('approved', 0)
            }
            
    def debug_payment_status(self) -> Dict:
        """Debug method to check payment consistency"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # All payments
            cursor.execute("SELECT COUNT(*), status FROM payments GROUP BY status")
            status_counts = dict(cursor.fetchall())
            
            # Recent payments
            cursor.execute("""
                SELECT id, user_id, days, amount, status, trakteer_id, created_at 
                FROM payments 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
            recent_payments = cursor.fetchall()
            
            # VIP users vs approved payments
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE vip_expires_at IS NOT NULL 
                AND datetime(vip_expires_at) > datetime('now')
            """)
            active_vip_count = cursor.fetchone()[0]
            
            return {
                "status_counts": status_counts,
                "recent_payments": recent_payments,
                "active_vip_count": active_vip_count
            }
