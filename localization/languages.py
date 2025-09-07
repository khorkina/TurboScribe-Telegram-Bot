"""
Localization module for multilingual support
"""

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

MESSAGES = {
    'en': {
        'start': "🎵 Welcome to Audio/Video Transcription Bot!\n\nI can transcribe and translate your audio/video files.\n\n📊 You have {free_requests} free request(s) remaining today.\n\n📎 Send me an audio or video file to get started!",
        'help': "📋 How to use:\n1. Send me an audio or video file\n2. I'll transcribe it automatically\n3. Choose your target language\n4. Get the translation!\n\n💎 Premium: Unlimited requests for 5 ⭐ per month",
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
        'limit_reached': "🚫 Daily limit reached!\n\n💎 Subscribe for unlimited access: 5 ⭐ per month",
        'premium_user': "💎 Premium user - unlimited requests!",
        'subscribe_button': "💎 Subscribe (5 ⭐)",
        'subscription_successful': "🎉 Subscription successful! You now have unlimited access!",
        'subscription_failed': "❌ Subscription failed. Please try again.",
        'language_selected': "Language: {language}",
        'cancel': "Cancel",
        'back': "← Back"
    },
    'ru': {
        'start': "🎵 Добро пожаловать в бот транскрибации аудио/видео!\n\nЯ могу расшифровать и перевести ваши аудио/видео файлы.\n\n📊 У вас осталось {free_requests} бесплатных запроса(ов) на сегодня.\n\n📎 Отправьте мне аудио или видео файл для начала!",
        'help': "📋 Как пользоваться:\n1. Отправьте мне аудио или видео файл\n2. Я автоматически расшифрую его\n3. Выберите целевой язык\n4. Получите перевод!\n\n💎 Премиум: Безлимитные запросы за 5 ⭐ в месяц",
        'processing': "🔄 Обработка вашего файла...",
        'transcribing': "🎤 Расшифровка аудио...",
        'transcription_complete': "✅ Расшифровка завершена!\n\n📝 **Оригинальный текст:**\n{transcription}\n\n🌐 Выберите язык для перевода:",
        'translating': "🌐 Перевод на {language}...",
        'translation_complete': "✅ Перевод завершен!\n\n🌐 **Перевод на {language}:**\n{translation}",
        'file_too_large': "❌ Файл слишком большой! Максимальный размер: {max_size}МБ",
        'unsupported_format': "❌ Неподдерживаемый формат! Поддерживаются: аудио/видео файлы",
        'processing_error': "❌ Ошибка обработки файла. Попробуйте снова.",
        'no_transcription': "❌ Не удалось расшифровать аудио. Убедитесь, что оно содержит речь.",
        'translation_failed': "❌ Перевод не удался. Попробуйте снова.",
        'limit_reached': "🚫 Дневной лимит исчерпан!\n\n💎 Подпишитесь для безлимитного доступа: 5 ⭐ в месяц",
        'premium_user': "💎 Премиум пользователь - безлимитные запросы!",
        'subscribe_button': "💎 Подписаться (5 ⭐)",
        'subscription_successful': "🎉 Подписка успешна! Теперь у вас безлимитный доступ!",
        'subscription_failed': "❌ Подписка не удалась. Попробуйте снова.",
        'language_selected': "Язык: {language}",
        'cancel': "Отмена",
        'back': "← Назад"
    },
    'es': {
        'start': "🎵 ¡Bienvenido al bot de transcripción de audio/video!\n\nPuedo transcribir y traducir tus archivos de audio/video.\n\n📊 Te quedan {free_requests} solicitud(es) gratuita(s) hoy.\n\n📎 ¡Envíame un archivo de audio o video para empezar!",
        'help': "📋 Cómo usar:\n1. Envíame un archivo de audio o video\n2. Lo transcribiré automáticamente\n3. Elige tu idioma objetivo\n4. ¡Obtén la traducción!\n\n💎 Premium: Solicitudes ilimitadas por 5 ⭐ al mes",
        'processing': "🔄 Procesando tu archivo...",
        'transcribing': "🎤 Transcribiendo audio...",
        'transcription_complete': "✅ ¡Transcripción completa!\n\n📝 **Texto original:**\n{transcription}\n\n🌐 Elige idioma objetivo para traducción:",
        'translating': "🌐 Traduciendo a {language}...",
        'translation_complete': "✅ ¡Traducción completa!\n\n🌐 **Traducción al {language}:**\n{translation}",
        'file_too_large': "❌ ¡Archivo demasiado grande! Tamaño máximo: {max_size}MB",
        'unsupported_format': "❌ ¡Formato no soportado! Soportados: archivos de audio/video",
        'processing_error': "❌ Error procesando archivo. Inténtalo de nuevo.",
        'no_transcription': "❌ No se pudo transcribir el audio. Asegúrate de que contenga habla.",
        'translation_failed': "❌ Traducción falló. Inténtalo de nuevo.",
        'limit_reached': "🚫 ¡Límite diario alcanzado!\n\n💎 Suscríbete para acceso ilimitado: 5 ⭐ por mes",
        'premium_user': "💎 Usuario premium - ¡solicitudes ilimitadas!",
        'subscribe_button': "💎 Suscribirse (5 ⭐)",
        'subscription_successful': "🎉 ¡Suscripción exitosa! ¡Ahora tienes acceso ilimitado!",
        'subscription_failed': "❌ Suscripción falló. Inténtalo de nuevo.",
        'language_selected': "Idioma: {language}",
        'cancel': "Cancelar",
        'back': "← Atrás"
    }
}

def get_message(lang_code: str, key: str, **kwargs) -> str:
    """Get localized message"""
    lang = lang_code if lang_code in MESSAGES else 'en'
    message = MESSAGES[lang].get(key, MESSAGES['en'].get(key, key))
    
    if kwargs:
        try:
            return message.format(**kwargs)
        except:
            return message
    return message

def get_language_name(lang_code: str) -> str:
    """Get language name by code"""
    return LANGUAGES.get(lang_code, lang_code)