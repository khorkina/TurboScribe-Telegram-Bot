"""
Telegram Bot Handlers
"""
import os
import tempfile
import time
from typing import Dict, Any
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.models import db
from processors.audio_processor import audio_processor
from localization.languages import get_message, get_language_name, LANGUAGES
from bot.config import Config

router = Router()

class ProcessingState(StatesGroup):
    waiting_for_language = State()

@router.message(Command("start"))
async def start_command(message: Message):
    """Handle /start command"""
    user = message.from_user
    await db.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        language_code=user.language_code or 'en'
    )
    
    # Check remaining free requests
    can_request, request_type = await db.can_make_request(user.id)
    if request_type == "premium":
        free_requests = "∞"
    else:
        daily_usage = await db.get_daily_usage(user.id)
        free_requests = Config.DAILY_FREE_REQUESTS - daily_usage
    
    await message.answer(
        get_message(user.language_code, 'start', free_requests=free_requests)
    )

@router.message(Command("help"))
async def help_command(message: Message):
    """Handle /help command"""
    user = message.from_user
    await message.answer(get_message(user.language_code, 'help'))

@router.message(F.content_type.in_(['audio', 'video', 'document', 'voice', 'video_note']))
async def handle_media_file(message: Message, state: FSMContext):
    """Handle audio/video files"""
    user = message.from_user
    
    # Check if user can make request
    can_request, request_type = await db.can_make_request(user.id)
    if not can_request:
        # Show subscription button
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=get_message(user.language_code, 'subscribe_button'),
                callback_data="subscribe"
            )
        ]])
        await message.answer(
            get_message(user.language_code, 'limit_reached'),
            reply_markup=keyboard
        )
        return
    
    # Get file info
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
    else:
        await message.answer(get_message(user.language_code, 'unsupported_format'))
        return
    
    # Check file size
    if file_info.file_size and file_info.file_size > Config.MAX_FILE_SIZE_MB * 1024 * 1024:
        await message.answer(
            get_message(user.language_code, 'file_too_large', 
                       max_size=Config.MAX_FILE_SIZE_MB)
        )
        return
    
    # Check file format
    file_type, needs_extraction = audio_processor.get_file_format(filename)
    if file_type == "unsupported":
        await message.answer(get_message(user.language_code, 'unsupported_format'))
        return
    
    # Start processing
    status_msg = await message.answer(get_message(user.language_code, 'processing'))
    
    start_time = time.time()
    
    try:
        # Download file
        file_obj = await message.bot.get_file(file_info.file_id)
        file_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file_obj.file_path}"
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_file:
            temp_path = tmp_file.name
        
        # Download and process file
        downloaded_path = await audio_processor.download_file(temp_path, file_url)
        if not downloaded_path:
            await status_msg.edit_text(get_message(user.language_code, 'processing_error'))
            return
        
        # Update status
        await status_msg.edit_text(get_message(user.language_code, 'transcribing'))
        
        # Transcribe (without translation for now)
        transcription, _, process_status = await audio_processor.process_file(
            downloaded_path, filename, "en"  # Temporary language
        )
        
        if process_status != "success" or not transcription:
            error_msg = {
                'extraction_failed': 'processing_error',
                'transcription_failed': 'no_transcription',
                'processing_error': 'processing_error'
            }.get(process_status, 'processing_error')
            await status_msg.edit_text(get_message(user.language_code, error_msg))
            return
        
        # Show transcription and language selection
        keyboard = create_language_keyboard(user.language_code)
        
        await status_msg.edit_text(
            get_message(user.language_code, 'transcription_complete', 
                       transcription=transcription[:1000] + ("..." if len(transcription) > 1000 else "")),
            reply_markup=keyboard
        )
        
        # Save state
        await state.set_state(ProcessingState.waiting_for_language)
        await state.update_data({
            'transcription': transcription,
            'file_path': downloaded_path,
            'filename': filename,
            'file_type': file_type,
            'start_time': start_time
        })
        
        # Increment usage if not premium
        if request_type != "premium":
            await db.increment_daily_usage(user.id)
    
    except Exception as e:
        print(f"Error processing file: {e}")
        await status_msg.edit_text(get_message(user.language_code, 'processing_error'))
    
    finally:
        # Clean up temp file
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass

def create_language_keyboard(user_lang: str) -> InlineKeyboardMarkup:
    """Create language selection keyboard"""
    buttons = []
    row = []
    
    for lang_code, lang_name in LANGUAGES.items():
        if lang_code != user_lang:  # Don't show user's current language
            button = InlineKeyboardButton(
                text=f"{lang_name}",
                callback_data=f"translate_{lang_code}"
            )
            row.append(button)
            
            if len(row) == 2:
                buttons.append(row)
                row = []
    
    if row:  # Add remaining buttons
        buttons.append(row)
    
    # Add cancel button
    buttons.append([InlineKeyboardButton(
        text=get_message(user_lang, 'cancel'),
        callback_data="cancel"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.callback_query(F.data.startswith("translate_"))
async def handle_translation(callback_query: CallbackQuery, state: FSMContext):
    """Handle translation language selection"""
    user = callback_query.from_user
    lang_code = callback_query.data.split("_")[1]
    
    # Get state data
    data = await state.get_data()
    if not data or 'transcription' not in data:
        await callback_query.answer("Session expired. Please send file again.")
        return
    
    transcription = data['transcription']
    file_path = data.get('file_path')
    start_time = data.get('start_time', time.time())
    
    # Update message
    lang_name = get_language_name(lang_code)
    await callback_query.message.edit_text(
        get_message(user.language_code, 'translating', language=lang_name)
    )
    
    try:
        # Translate text
        translation = await audio_processor.translate_text(transcription, lang_name)
        
        if translation:
            await callback_query.message.edit_text(
                get_message(user.language_code, 'translation_complete',
                           language=lang_name, translation=translation)
            )
            
            # Save to history
            processing_time = int(time.time() - start_time)
            await db.add_request_history(
                user_id=user.id,
                file_type=data.get('file_type', 'unknown'),
                original_lang='auto',
                target_lang=lang_code,
                transcription=transcription,
                translation=translation,
                processing_time=processing_time
            )
        else:
            await callback_query.message.edit_text(
                get_message(user.language_code, 'translation_failed')
            )
    
    except Exception as e:
        print(f"Translation error: {e}")
        await callback_query.message.edit_text(
            get_message(user.language_code, 'translation_failed')
        )
    
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
    user = callback_query.from_user
    
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
    """Handle subscription request"""
    user = callback_query.from_user
    
    # Create Stars payment invoice
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
    
    try:
        # This is a placeholder - actual Telegram Stars implementation
        # would require proper setup with Bot API
        await callback_query.message.answer(
            "💎 Subscription feature will be available soon!\n\n"
            "For now, the bot is in beta mode with free usage.",
        )
        await callback_query.answer()
    except Exception as e:
        print(f"Subscription error: {e}")
        await callback_query.answer(
            get_message(user.language_code, 'subscription_failed'),
            show_alert=True
        )

@router.message()
async def handle_other_messages(message: Message):
    """Handle other messages"""
    user = message.from_user
    await message.answer(
        "📎 Please send me an audio or video file to transcribe and translate!\n\n"
        "Use /help for more information."
    )