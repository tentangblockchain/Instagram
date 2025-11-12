import os
import requests
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urlencode
from config import Config

logger = logging.getLogger(__name__)

class TrakteerAPI:
    def __init__(self):
        self.config = Config()
        self.base_url = "https://api.trakteer.id"
        self.headers = {
            "key": self.config.TRAKTEER_API_KEY,
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest"
        }
    
    def generate_payment_url(self, user_id: int, days: int, amount: int, quantity: int) -> str:
        """Generate Trakteer payment URL with user info in support message"""
        
        # Create support message that encodes user_id and days (simple format)
        supporter_message = f"{user_id} {days}"
        
        # Clean username for display (remove @ if present)
        clean_username = self.config.TRAKTEER_USERNAME.replace("@", "")
        
        # Trakteer payment URL parameters - matching the format you specified
        params = {
            "quantity": quantity,
            "step": "2",
            "display_name": clean_username,
            "supporter_message": supporter_message
        }
        
        # Generate the payment URL
        payment_url = f"https://trakteer.id/{self.config.TRAKTEER_USERNAME}/tip?" + urlencode(params)
        
        logger.info(f"Generated payment URL for user {user_id}, {days} days, quantity {quantity}")
        
        return payment_url
    
    def parse_support_message(self, support_message: str) -> Optional[Dict]:
        """Parse support message to extract user_id and days"""
        try:
            # Primary format: "user_id days" (simple space-separated)
            pattern = r"(\d+)\s+(\d+)"
            match = re.search(pattern, support_message)
            
            if match:
                user_id = int(match.group(1))
                days = int(match.group(2))
                return {"user_id": user_id, "days": days}
            
            # Fallback: try VIP format for backwards compatibility
            if support_message.startswith('VIP_') and support_message.endswith('days'):
                middle_part = support_message[4:-4]
                parts = middle_part.split('_')
                
                if len(parts) >= 2:
                    user_id = int(parts[0])
                    days = int(parts[1])
                    return {"user_id": user_id, "days": days}
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing support message '{support_message}': {e}")
            return None
    
    def get_transactions(self, limit: int = 50) -> List[Dict]:
        """Get recent transactions from Trakteer API - using correct endpoint"""
        try:
            # Use correct Trakteer API endpoint for supports (donations)
            url = "https://api.trakteer.id/v1/public/supports"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Trakteer API response: {data}")
            
            # Parse Trakteer API response format
            if isinstance(data, dict) and data.get("status") == "success":
                # Handle Trakteer API standard response format
                if data.get("result") and data["result"].get("data"):
                    supports = data["result"]["data"]
                    logger.info(f"Found {len(supports)} supports in API response")
                    # All payments from API are considered successful
                    return supports
                else:
                    logger.warning(f"No data found in result: {data}")
                    return []
            elif isinstance(data, list):
                # Direct list response - fallback
                return data
            else:
                logger.error(f"Unexpected response format: {data}")
                return []
                
        except requests.RequestException as e:
            logger.error(f"Network error fetching transactions: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching transactions: {e}")
            return []
    
    def get_transaction_by_id(self, transaction_id: str) -> Optional[Dict]:
        """Get specific transaction by ID"""
        try:
            url = f"{self.base_url}/v1/transactions/{transaction_id}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") == "success":
                return data.get("data")
            else:
                logger.error(f"Trakteer API error: {data.get('message', 'Unknown error')}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Network error fetching transaction {transaction_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching transaction {transaction_id}: {e}")
            return None
    
    async def sync_payments(self) -> List[Dict]:
        """Sync payments from Trakteer and update database"""
        from database import Database
        
        db = Database()
        new_payments = []
        
        try:
            # Get recent transactions
            transactions = self.get_transactions(limit=100)
            logger.info(f"Retrieved {len(transactions)} transactions from Trakteer API")
            
            for transaction in transactions:
                # Parse transaction data from Trakteer API response format
                support_message = transaction.get("support_message", "")
                quantity = transaction.get("quantity", 1)
                amount = transaction.get("amount", 0)
                supporter_name = transaction.get("supporter_name", "Unknown")
                updated_at = transaction.get("updated_at", "")
                # Generate unique ID from transaction data since no order_id in this format
                trakteer_id = f"trakteer_{hash(f'{supporter_name}_{support_message}_{amount}_{updated_at}')}"
                
                logger.info(f"Processing transaction: {trakteer_id}, message: '{support_message}', quantity: {quantity}, amount: {amount}")
                
                # Parse support message format: "user_id days"
                parsed = self.parse_support_message(support_message)
                
                if not parsed:
                    logger.warning(f"Skipping transaction {trakteer_id}: Invalid support message format '{support_message}'")
                    continue
                
                user_id = parsed["user_id"]
                days = parsed["days"]
                
                # Validate payment against VIP package
                if not self.validate_payment(user_id, amount, days):
                    logger.warning(f"Payment validation failed for user {user_id}: amount {amount}, days {days}")
                    # Still process but mark for manual review
                
                # Validate quantity matches expected package quantity
                expected_quantity = self.get_expected_quantity(days)
                if quantity != expected_quantity:
                    logger.warning(f"Quantity mismatch for {days} days package: expected {expected_quantity}, got {quantity}")
                
                # PRIMARY CHECK: Check if payment with same Trakteer ID already exists
                existing_payment = db.get_payment_by_trakteer_id(trakteer_id)
                if existing_payment:
                    logger.info(f"Payment {trakteer_id} already exists with status: {existing_payment['status']}, skipping")
                    continue
                
                # FINAL FIX: Skip all secondary checks for existing trakteer_id
                # The trakteer_id is unique per transaction, so if it doesn't exist above, it's truly new
                logger.info(f"New unique transaction: {trakteer_id} for user {user_id}")
                
                # TERTIARY CHECK: Even if user VIP expired/removed, don't process old transactions
                # Check if this Trakteer transaction is older than 36 hours
                from datetime import datetime, timedelta
                try:
                    transaction_time = datetime.strptime(updated_at, '%Y-%m-%d %H:%M:%S')
                    if datetime.now() - transaction_time > timedelta(hours=36):
                        logger.info(f"Skipping old transaction {trakteer_id} from {updated_at} (older than 36 hours)")
                        continue
                except Exception:
                    # If parsing fails, continue with processing
                    pass
                
                # QUATERNARY CHECK: Check if user ever had VIP from this payment amount/days combo
                # This prevents reprocessing when VIP naturally expires
                has_payment_history = db.has_processed_payment_combination(user_id, amount, days)
                if has_payment_history:
                    logger.info(f"User {user_id} already has payment history for {days} days / Rp{amount:,} - skipping duplicate")
                    continue
                
                # Additional check: if user has active VIP - don't create duplicate payments
                vip_status = db.get_vip_status(user_id)
                if vip_status and vip_status.get('is_active'):
                    logger.info(f"User {user_id} already has active VIP until {vip_status['expires_at']}, skipping payment creation")
                    continue
                
                # Record new payment as pending (needs admin approval)
                payment_id = db.record_payment(
                    user_id=user_id,
                    days=days,
                    amount=amount,
                    status="pending",
                    trakteer_id=trakteer_id
                )
                
                new_payments.append({
                    "id": payment_id,
                    "user_id": user_id,
                    "days": days,
                    "amount": amount,
                    "quantity": quantity,
                    "supporter_name": supporter_name,
                    "trakteer_id": trakteer_id,
                    "created_at": updated_at,
                    "validation_passed": self.validate_payment(user_id, amount, days) and quantity == expected_quantity
                })
                
                logger.info(f"New payment detected: User {user_id}, {days} days, Amount Rp{amount:,}, Quantity {quantity}")
            
            logger.info(f"Sync completed: {len(new_payments)} new payments found")
            return new_payments
            
        except Exception as e:
            logger.error(f"Error syncing payments: {e}")
            return []
    
    def get_expected_quantity(self, days: int) -> int:
        """Get expected quantity for VIP package"""
        from main import JawaneseTikTokBot
        
        bot = JawaneseTikTokBot()
        return bot.vip_packages.get(days, {}).get("quantity", 0)
    
    def validate_payment(self, user_id: int, amount: int, days: int) -> bool:
        """Validate payment amount against expected VIP package price"""
        from main import JawaneseTikTokBot
        
        bot = JawaneseTikTokBot()
        expected_price = bot.vip_packages.get(days, {}).get("price", 0)
        
        if expected_price == 0:
            logger.warning(f"No package found for {days} days")
            return False
        
        # Allow some tolerance for payment fees (±5%)
        min_amount = expected_price * 0.95
        max_amount = expected_price * 1.05
        
        is_valid = min_amount <= amount <= max_amount
        logger.info(f"Payment validation for {days} days: expected {expected_price}, got {amount}, valid: {is_valid}")
        
        return is_valid
    
    def get_payment_stats(self) -> Dict:
        """Get payment statistics"""
        try:
            transactions = self.get_transactions(limit=1000)
            
            total_amount = sum(t.get("amount", 0) for t in transactions)
            total_count = len(transactions)
            
            # Group by days
            package_stats = {}
            for transaction in transactions:
                support_message = transaction.get("support_message", "")
                parsed = self.parse_support_message(support_message)
                
                if parsed:
                    days = parsed["days"]
                    if days not in package_stats:
                        package_stats[days] = {"count": 0, "total_amount": 0}
                    
                    package_stats[days]["count"] += 1
                    package_stats[days]["total_amount"] += transaction.get("amount", 0)
            
            return {
                "total_amount": total_amount,
                "total_count": total_count,
                "package_stats": package_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting payment stats: {e}")
            return {"total_amount": 0, "total_count": 0, "package_stats": {}}
