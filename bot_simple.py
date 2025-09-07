#!/usr/bin/env python3
"""
Simplified Telegram Bot for Audio/Video Transcription and Translation
"""

import asyncio
import logging
import os
import tempfile
import time
from typing import Optional, Tuple
from datetime import datetime, timedelta

# Third party imports
import asyncpg
import aiohttp
import aiofiles
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

DAILY_FREE_REQUESTS = 3
MAX_FILE_SIZE_MB = 100
SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}
SUPPORTED_VIDEO_FORMATS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

# Languages mapping
LANGUAGES = {
    'en': 'English',
    'ru': 'Русский',
    'es': 'Español', 
    'fr': 'Français',
    'de': 'Deutsch',
    'it': 'Italiano',
    'pt': 'Português',
    'zh': '中文',
    'ja': '日本語',
    'ko': '한국어',
    'ar': 'العربية',
    'hi': 'हिन्दी'
}

# Simple messages
MESSAGES = {
    'start': "🎵 Welcome to Audio/Video Transcription Bot!\n\nI can transcribe and translate your audio/video files.\n\n📊 You have {free_requests} free request(s) remaining today (3 per day).\n\n📎 Send me an audio or video file to get started!",
    'help': "📋 How to use:\n1. Send me an audio or video file\n2. I'll transcribe it automatically\n3. Choose your target language\n4. Get the translation!\n\n🆓 Free: 3 requests per day\n💎 Premium: Unlimited requests for 5 ⭐ per month",
    'processing': "🔄 Processing your file...",
    'transcribing': "🎤 Transcribing audio...",
    'transcription_complete': "✅ Transcription complete!\n\n📝 **Original text:**\n{transcription}\n\n🌐 Choose target language for translation:",
    'translating': "🌐 Translating to {language}...",
    'translation_complete': "✅ Translation complete!\n\n🌐 **{language} translation:**\n{translation}",
    'file_too_large': "❌ File too large! Maximum size: {max_size}MB",
    'unsupported_format': "❌ Unsupported file format! Supported: audio/video files",
    'processing_error': "❌ Error processing file. Please try again.",
    'no_transcription': "❌ Could not transcribe audio. Please ensure it contains speech.",
    'translation_failed': "❌ Translation failed. Please try again.",
    'limit_reached': "🚫 Daily limit reached! (3 requests per day)\n\n💎 Subscribe for unlimited access: 5 ⭐ per month",
    'premium_user': "💎 Premium user - unlimited requests!",
    'subscribe_button': "💎 Subscribe (5 ⭐)",
    'subscription_successful': "🎉 Subscription successful! You now have unlimited access!",
    'subscription_failed': "❌ Subscription failed. Please try again.",
    'language_selected': "Language: {language}",
    'cancel': "Cancel",
    'back': "← Back"
}

# Database pool
db_pool = None
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

class ProcessingState(StatesGroup):
    waiting_for_language = State()

# Initialize router
router = Router()

async def init_database():
    """Initialize database connection"""
    global db_pool
    if not DATABASE_URL:
        logging.warning("DATABASE_URL not set, using in-memory storage")
        return
    
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
        
        # Create tables
        async with db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(100),
                    first_name VARCHAR(100),
                    language_code VARCHAR(10) DEFAULT 'en',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_usage (
                    user_id BIGINT,
                    usage_date DATE DEFAULT CURRENT_DATE,
                    requests_count INTEGER DEFAULT 0,
                    PRIMARY KEY(user_id, usage_date)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    user_id BIGINT PRIMARY KEY,
                    is_premium BOOLEAN DEFAULT FALSE,
                    subscription_start TIMESTAMP,
                    subscription_end TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS payment_records (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    telegram_payment_charge_id VARCHAR(200),
                    amount_stars INTEGER,
                    invoice_payload VARCHAR(200),
                    status VARCHAR(50) DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")

async def get_daily_usage(user_id: int) -> int:
    """Get user's daily usage count"""
    if not db_pool:
        return 0
    
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT requests_count FROM daily_usage 
                WHERE user_id = $1 AND usage_date = CURRENT_DATE
            """, user_id)
            return result['requests_count'] if result else 0
    except:
        return 0

async def increment_daily_usage(user_id: int) -> int:
    """Increment user's daily usage"""
    if not db_pool:
        return 1
    
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchrow("""
                INSERT INTO daily_usage (user_id, requests_count) 
                VALUES ($1, 1) 
                ON CONFLICT (user_id, usage_date) 
                DO UPDATE SET requests_count = daily_usage.requests_count + 1 
                RETURNING requests_count
            """, user_id)
            return result['requests_count'] if result else 1
    except:
        return 1

async def is_user_premium(user_id: int) -> bool:
    """Check if user has active premium subscription"""
    if not db_pool:
        return False
    
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT is_premium, subscription_end FROM user_subscriptions 
                WHERE user_id = $1
            """, user_id)
            
            if not result:
                # Create subscription record
                await conn.execute("""
                    INSERT INTO user_subscriptions (user_id, is_premium) 
                    VALUES ($1, FALSE)
                    ON CONFLICT (user_id) DO NOTHING
                """, user_id)
                return False
            
            if not result['is_premium']:
                return False
            
            # Check if subscription expired
            if result['subscription_end']:
                from datetime import datetime
                if result['subscription_end'] < datetime.now():
                    # Subscription expired, update status
                    await conn.execute("""
                        UPDATE user_subscriptions SET is_premium = FALSE 
                        WHERE user_id = $1
                    """, user_id)
                    return False
            
            return True
    except Exception as e:
        logging.error(f"Error checking premium status: {e}")
        return False

async def activate_premium_subscription(user_id: int, duration_days: int = 30):
    """Activate premium subscription for user"""
    if not db_pool:
        return
    
    try:
        from datetime import datetime, timedelta
        subscription_end = datetime.now() + timedelta(days=duration_days)
        
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_subscriptions 
                (user_id, is_premium, subscription_start, subscription_end, updated_at) 
                VALUES ($1, TRUE, CURRENT_TIMESTAMP, $2, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    is_premium = TRUE, 
                    subscription_start = CURRENT_TIMESTAMP,
                    subscription_end = $2,
                    updated_at = CURRENT_TIMESTAMP
            """, user_id, subscription_end)
            
            logging.info(f"Premium activated for user {user_id} until {subscription_end}")
    except Exception as e:
        logging.error(f"Error activating premium: {e}")

async def save_payment_record(user_id: int, payment_charge_id: str, amount: int, payload: str):
    """Save payment record to database"""
    if not db_pool:
        return
    
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO payment_records 
                (user_id, telegram_payment_charge_id, amount_stars, invoice_payload) 
                VALUES ($1, $2, $3, $4)
            """, user_id, payment_charge_id, amount, payload)
            logging.info(f"Payment record saved for user {user_id}: {amount} stars")
    except Exception as e:
        logging.error(f"Error saving payment record: {e}")

async def can_make_request(user_id: int) -> tuple[bool, str]:
    """Check if user can make a request"""
    is_premium = await is_user_premium(user_id)
    
    if is_premium:
        return True, "premium"
    
    daily_usage = await get_daily_usage(user_id)
    if daily_usage < DAILY_FREE_REQUESTS:
        return True, "free"
    
    return False, "limit_exceeded"

async def download_file(file_path: str, file_url: str) -> Optional[str]:
    """Download file from Telegram servers"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(1024):
                            await f.write(chunk)
                    return file_path
    except Exception as e:
        logging.error(f"Error downloading file: {e}")
        return None

async def transcribe_audio(audio_path: str) -> Optional[str]:
    """Transcribe audio file using OpenAI Whisper"""
    if not openai_client:
        return "Demo transcription: This is a sample transcription for testing purposes."
    
    try:
        with open(audio_path, 'rb') as audio_file:
            transcript = await openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return str(transcript)
    except Exception as e:
        logging.error(f"Error transcribing audio: {e}")
        return None

async def translate_text(text: str, target_language: str) -> Optional[str]:
    """Translate text using OpenAI GPT"""
    if not openai_client:
        return f"Demo translation to {target_language}: {text[:100]}..."
    
    try:
        prompt = f"""Translate the following text to {target_language}. 
If the text is already in {target_language}, return it as is.

Text to translate:
{text}

Translation:"""
        
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional translator. Provide only the translation without any additional comments or explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error translating text: {e}")
        return None

def get_file_format(filename: str) -> Tuple[str, bool]:
    """Determine file format and if it needs audio extraction"""
    ext = os.path.splitext(filename.lower())[1]
    
    if ext in SUPPORTED_AUDIO_FORMATS:
        return "audio", False
    elif ext in SUPPORTED_VIDEO_FORMATS:
        return "video", True
    else:
        return "unsupported", False

@router.message(Command("start"))
async def start_command(message: Message):
    """Handle /start command"""
    if not message.from_user:
        return
        
    user = message.from_user
    is_premium = await is_user_premium(user.id)
    
    if is_premium:
        free_requests = "∞ (Premium)"
    else:
        daily_usage = await get_daily_usage(user.id)
        free_requests = max(0, DAILY_FREE_REQUESTS - daily_usage)
    
    await message.answer(
        MESSAGES['start'].format(free_requests=free_requests)
    )

@router.message(Command("help"))
async def help_command(message: Message):
    """Handle /help command"""
    await message.answer(MESSAGES['help'])

@router.message(Command("status"))
async def status_command(message: Message):
    """Handle /status command - show user's subscription status"""
    if not message.from_user:
        return
        
    user = message.from_user
    is_premium = await is_user_premium(user.id)
    daily_usage = await get_daily_usage(user.id)
    
    if is_premium:
        status_text = (
            "💎 **Premium User**\n\n"
            "✅ Unlimited transcriptions\n"
            "✅ Unlimited translations\n"
            "✅ Priority processing\n\n"
            f"📊 Today's usage: {daily_usage} requests"
        )
    else:
        remaining = max(0, DAILY_FREE_REQUESTS - daily_usage)
        status_text = (
            "🆓 **Free User**\n\n"
            f"📊 Today's usage: {daily_usage}/{DAILY_FREE_REQUESTS}\n"
            f"📈 Remaining: {remaining} requests\n\n"
            "💎 Upgrade to Premium for unlimited access!"
        )
        
        if remaining == 0:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=MESSAGES['subscribe_button'],
                    callback_data="subscribe"
                )
            ]])
            await message.answer(status_text, reply_markup=keyboard)
            return
    
    await message.answer(status_text)

@router.message(F.content_type.in_(['audio', 'video', 'document', 'voice', 'video_note']))
async def handle_media_file(message: Message, state: FSMContext):
    """Handle audio/video files"""
    if not message.from_user:
        return
        
    user = message.from_user
    
    # Check if user can make request
    can_request, request_type = await can_make_request(user.id)
    if not can_request:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=MESSAGES['subscribe_button'],
                callback_data="subscribe"
            )
        ]])
        await message.answer(MESSAGES['limit_reached'], reply_markup=keyboard)
        return
    
    # Get file info
    file_info = None
    filename = "unknown"
    
    if message.content_type == 'audio' and message.audio:
        file_info = message.audio
        filename = message.audio.file_name or f"audio_{message.audio.file_id}.mp3"
    elif message.content_type == 'video' and message.video:
        file_info = message.video
        filename = message.video.file_name or f"video_{message.video.file_id}.mp4"
    elif message.content_type == 'document' and message.document:
        file_info = message.document
        filename = message.document.file_name or f"document_{message.document.file_id}"
    elif message.content_type == 'voice' and message.voice:
        file_info = message.voice
        filename = f"voice_{message.voice.file_id}.ogg"
    elif message.content_type == 'video_note' and message.video_note:
        file_info = message.video_note
        filename = f"video_note_{message.video_note.file_id}.mp4"
    
    if not file_info:
        await message.answer(MESSAGES['unsupported_format'])
        return
    
    # Check file size
    if hasattr(file_info, 'file_size') and file_info.file_size and file_info.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        await message.answer(MESSAGES['file_too_large'].format(max_size=MAX_FILE_SIZE_MB))
        return
    
    # Check file format
    file_type, needs_extraction = get_file_format(filename)
    if file_type == "unsupported":
        await message.answer(MESSAGES['unsupported_format'])
        return
    
    # Start processing
    status_msg = await message.answer(MESSAGES['processing'])
    
    try:
        # Download file
        file_obj = await message.bot.get_file(file_info.file_id)
        file_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file_obj.file_path}"
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_file:
            temp_path = tmp_file.name
        
        # Download file
        downloaded_path = await download_file(temp_path, file_url)
        if not downloaded_path:
            await status_msg.edit_text(MESSAGES['processing_error'])
            return
        
        # Update status
        await status_msg.edit_text(MESSAGES['transcribing'])
        
        # Transcribe audio
        transcription = await transcribe_audio(downloaded_path)
        if not transcription:
            await status_msg.edit_text(MESSAGES['no_transcription'])
            return
        
        # Show transcription and language selection
        keyboard = create_language_keyboard()
        
        await status_msg.edit_text(
            MESSAGES['transcription_complete'].format(
                transcription=transcription[:1000] + ("..." if len(transcription) > 1000 else "")
            ),
            reply_markup=keyboard
        )
        
        # Save state
        await state.set_state(ProcessingState.waiting_for_language)
        await state.update_data({
            'transcription': transcription,
            'file_path': downloaded_path,
            'filename': filename
        })
        
        # Increment usage if not premium
        if request_type != "premium":
            await increment_daily_usage(user.id)
    
    except Exception as e:
        logging.error(f"Error processing file: {e}")
        await status_msg.edit_text(MESSAGES['processing_error'])
    
    finally:
        # Clean up temp file
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass

def create_language_keyboard() -> InlineKeyboardMarkup:
    """Create language selection keyboard"""
    buttons = []
    row = []
    
    for lang_code, lang_name in list(LANGUAGES.items())[:8]:  # Limit to 8 languages
        button = InlineKeyboardButton(
            text=f"{lang_name}",
            callback_data=f"translate_{lang_code}"
        )
        row.append(button)
        
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    # Add cancel button
    buttons.append([InlineKeyboardButton(
        text=MESSAGES['cancel'],
        callback_data="cancel"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.callback_query(F.data.startswith("translate_"))
async def handle_translation(callback_query: CallbackQuery, state: FSMContext):
    """Handle translation language selection"""
    if not callback_query.from_user or not callback_query.message:
        return
        
    user = callback_query.from_user
    lang_code = callback_query.data.split("_")[1]
    
    # Get state data
    data = await state.get_data()
    if not data or 'transcription' not in data:
        await callback_query.answer("Session expired. Please send file again.")
        return
    
    transcription = data['transcription']
    file_path = data.get('file_path')
    
    # Update message
    lang_name = LANGUAGES.get(lang_code, lang_code)
    await callback_query.message.edit_text(
        MESSAGES['translating'].format(language=lang_name)
    )
    
    try:
        # Translate text
        translation = await translate_text(transcription, lang_name)
        
        if translation:
            await callback_query.message.edit_text(
                MESSAGES['translation_complete'].format(
                    language=lang_name, 
                    translation=translation
                )
            )
        else:
            await callback_query.message.edit_text(MESSAGES['translation_failed'])
    
    except Exception as e:
        logging.error(f"Translation error: {e}")
        await callback_query.message.edit_text(MESSAGES['translation_failed'])
    
    finally:
        # Clear state and clean up
        await state.clear()
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
    
    await callback_query.answer()

@router.callback_query(F.data == "cancel")
async def handle_cancel(callback_query: CallbackQuery, state: FSMContext):
    """Handle cancel button"""
    if not callback_query.message:
        return
        
    # Clean up state and files
    data = await state.get_data()
    if data and 'file_path' in data:
        file_path = data['file_path']
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
    
    await state.clear()
    await callback_query.message.delete()
    await callback_query.answer()

@router.callback_query(F.data == "subscribe")
async def handle_subscription(callback_query: CallbackQuery):
    """Handle subscription request - create Telegram Stars invoice"""
    if not callback_query.from_user or not callback_query.message:
        return
        
    try:
        user_id = callback_query.from_user.id
        
        # Create invoice for 5 Telegram Stars (monthly subscription)
        prices = [LabeledPrice(label="Premium Monthly Subscription", amount=5)]
        
        await callback_query.message.bot.send_invoice(
            chat_id=callback_query.message.chat.id,
            title="💎 Premium Subscription",
            description="Get unlimited transcriptions and translations for 1 month!\n\n✅ Unlimited requests\n✅ Priority processing\n✅ No daily limits",
            payload=f"premium_subscription_{user_id}",
            provider_token="",  # Empty for Telegram Stars
            currency="XTR",  # Telegram Stars currency
            prices=prices,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="💎 Pay 5 ⭐", pay=True)
            ]])
        )
        
        await callback_query.answer("Invoice sent! Complete payment to activate premium.")
        
    except Exception as e:
        logging.error(f"Subscription error: {e}")
        await callback_query.answer(MESSAGES['subscription_failed'], show_alert=True)

@router.pre_checkout_query()
async def handle_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Handle pre-checkout validation"""
    try:
        # Validate the payment
        user_id = pre_checkout_query.from_user.id
        payload = pre_checkout_query.invoice_payload
        
        logging.info(f"Pre-checkout for user {user_id}, payload: {payload}")
        
        # Validate that this is a premium subscription
        if not payload.startswith("premium_subscription_"):
            await pre_checkout_query.bot.answer_pre_checkout_query(
                pre_checkout_query.id, 
                ok=False, 
                error_message="Invalid subscription type"
            )
            return
        
        # All checks passed
        await pre_checkout_query.bot.answer_pre_checkout_query(
            pre_checkout_query.id, 
            ok=True
        )
        
    except Exception as e:
        logging.error(f"Pre-checkout error: {e}")
        await pre_checkout_query.bot.answer_pre_checkout_query(
            pre_checkout_query.id, 
            ok=False, 
            error_message="Payment validation failed"
        )

@router.message(F.content_type == 'successful_payment')
async def handle_successful_payment(message: Message):
    """Handle successful payment - activate premium subscription"""
    if not message.from_user or not message.successful_payment:
        return
        
    try:
        user_id = message.from_user.id
        payment = message.successful_payment
        
        # Save payment record
        await save_payment_record(
            user_id=user_id,
            payment_charge_id=payment.telegram_payment_charge_id,
            amount=payment.total_amount,
            payload=payment.invoice_payload
        )
        
        # Activate premium subscription for 30 days
        await activate_premium_subscription(user_id, duration_days=30)
        
        # Send success message
        await message.answer(
            "🎉 **Payment Successful!**\n\n"
            "✅ Premium subscription activated!\n"
            "✅ Unlimited transcriptions and translations\n" 
            "✅ Valid for 30 days\n\n"
            "Thank you for supporting our service! 💎"
        )
        
        logging.info(f"Premium subscription activated for user {user_id}")
        
    except Exception as e:
        logging.error(f"Payment processing error: {e}")
        await message.answer(
            "❌ There was an error activating your subscription. "
            "Please contact support if the issue persists."
        )

@router.message()
async def handle_other_messages(message: Message):
    """Handle other messages"""
    await message.answer(
        "📎 Please send me an audio or video file to transcribe and translate!\n\n"
        "Use /help for more information."
    )

async def main():
    """Main function to run the bot"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Check required environment variables
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is not set!")
        return
    
    logging.info("Starting Telegram Bot...")
    
    # Initialize database
    await init_database()
    
    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Register handlers
    dp.include_router(router)
    
    # Log startup
    try:
        bot_info = await bot.get_me()
        logging.info(f"Bot @{bot_info.username} started successfully!")
        
        # Start polling
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Bot error: {e}")
        raise
    finally:
        # Cleanup
        if db_pool:
            await db_pool.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())