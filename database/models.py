"""
Database models for the Telegram bot
"""
import asyncpg
from datetime import datetime, timedelta
from typing import Optional
from bot.config import Config


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(Config.DATABASE_URL)
        await self.create_tables()
    
    async def close(self):
        """Close database connection"""
        if self.pool:
            await self.pool.close()
    
    async def create_tables(self):
        """Create necessary database tables"""
        async with self.pool.acquire() as conn:
            # Users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(100),
                    first_name VARCHAR(100),
                    language_code VARCHAR(10) DEFAULT 'en',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User subscriptions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    user_id BIGINT PRIMARY KEY REFERENCES users(user_id),
                    is_premium BOOLEAN DEFAULT FALSE,
                    subscription_start TIMESTAMP,
                    subscription_end TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Daily usage tracking
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_usage (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    usage_date DATE DEFAULT CURRENT_DATE,
                    requests_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, usage_date)
                )
            """)
            
            # Request history
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS request_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    file_type VARCHAR(20),
                    original_language VARCHAR(10),
                    target_language VARCHAR(10),
                    transcription_text TEXT,
                    translated_text TEXT,
                    processing_time_seconds INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    async def get_or_create_user(self, user_id: int, username: str = None, 
                                first_name: str = None, language_code: str = 'en') -> dict:
        """Get or create user in database"""
        async with self.pool.acquire() as conn:
            # Try to get existing user
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1", user_id
            )
            
            if user:
                # Update user info if changed
                await conn.execute("""
                    UPDATE users SET 
                        username = $2, 
                        first_name = $3, 
                        language_code = $4, 
                        updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = $1
                """, user_id, username, first_name, language_code)
                return dict(user)
            else:
                # Create new user
                await conn.execute("""
                    INSERT INTO users (user_id, username, first_name, language_code) 
                    VALUES ($1, $2, $3, $4)
                """, user_id, username, first_name, language_code)
                
                # Create subscription record
                await conn.execute("""
                    INSERT INTO user_subscriptions (user_id, is_premium) 
                    VALUES ($1, FALSE)
                """, user_id)
                
                return {
                    'user_id': user_id,
                    'username': username,
                    'first_name': first_name,
                    'language_code': language_code,
                    'created_at': datetime.now()
                }
    
    async def get_daily_usage(self, user_id: int) -> int:
        """Get user's daily usage count"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT requests_count FROM daily_usage 
                WHERE user_id = $1 AND usage_date = CURRENT_DATE
            """, user_id)
            return result['requests_count'] if result else 0
    
    async def increment_daily_usage(self, user_id: int) -> int:
        """Increment user's daily usage and return new count"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                INSERT INTO daily_usage (user_id, requests_count) 
                VALUES ($1, 1) 
                ON CONFLICT (user_id, usage_date) 
                DO UPDATE SET requests_count = daily_usage.requests_count + 1 
                RETURNING requests_count
            """, user_id)
            return result['requests_count']
    
    async def is_user_premium(self, user_id: int) -> bool:
        """Check if user has active premium subscription"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT is_premium, subscription_end FROM user_subscriptions 
                WHERE user_id = $1
            """, user_id)
            
            if not result or not result['is_premium']:
                return False
            
            if result['subscription_end'] and result['subscription_end'] < datetime.now():
                # Subscription expired, update status
                await conn.execute("""
                    UPDATE user_subscriptions SET is_premium = FALSE 
                    WHERE user_id = $1
                """, user_id)
                return False
            
            return True
    
    async def activate_premium_subscription(self, user_id: int, duration_days: int = 30):
        """Activate premium subscription for user"""
        async with self.pool.acquire() as conn:
            subscription_end = datetime.now() + timedelta(days=duration_days)
            await conn.execute("""
                UPDATE user_subscriptions SET 
                    is_premium = TRUE, 
                    subscription_start = CURRENT_TIMESTAMP,
                    subscription_end = $2,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1
            """, user_id, subscription_end)
    
    async def can_make_request(self, user_id: int) -> tuple[bool, str]:
        """Check if user can make a request"""
        is_premium = await self.is_user_premium(user_id)
        
        if is_premium:
            return True, "premium"
        
        daily_usage = await self.get_daily_usage(user_id)
        if daily_usage < Config.DAILY_FREE_REQUESTS:
            return True, "free"
        
        return False, "limit_exceeded"
    
    async def add_request_history(self, user_id: int, file_type: str, 
                                 original_lang: str, target_lang: str,
                                 transcription: str, translation: str,
                                 processing_time: int):
        """Add request to history"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO request_history 
                (user_id, file_type, original_language, target_language, 
                 transcription_text, translated_text, processing_time_seconds) 
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, user_id, file_type, original_lang, target_lang, 
                transcription, translation, processing_time)


# Global database instance
db = Database()