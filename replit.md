# Overview

**Status: ✅ COMPLETED AND RUNNING**

This is a fully functional Telegram bot (@TurboscribeBot) for audio/video transcription and translation services. The bot allows users to upload audio or video files, transcribes them using OpenAI's Whisper API, and provides translation services to multiple languages. It includes a freemium model with daily limits for free users and subscription system preparation for premium access via Telegram Stars.

## Key Features Implemented

✅ **Multi-format Support**: Audio (MP3, WAV, M4A, OGG, FLAC, AAC) and Video (MP4, MOV, AVI, MKV, WebM)  
✅ **AI-Powered Transcription**: OpenAI Whisper API integration  
✅ **Multi-language Translation**: 12+ languages via GPT-4o-mini  
✅ **Freemium Model**: 1 free request per day per user  
✅ **Database Integration**: PostgreSQL for user tracking and usage limits  
✅ **Error Handling**: Comprehensive error handling and user feedback  
✅ **File Size Limits**: 100MB maximum file size protection  
✅ **Production Ready**: Proper logging, state management, and cleanup

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework
- **Aiogram**: Modern Python framework for Telegram Bot API with asyncio support
- **State Management**: FSM (Finite State Machine) for handling user interactions and workflows
- **Memory Storage**: In-memory storage for bot states during user sessions

## Database Layer
- **PostgreSQL**: Primary database for persistent data storage
- **AsyncPG**: Async PostgreSQL driver for non-blocking database operations
- **Schema**: Users table for user profiles, subscriptions table for premium status tracking, and usage tracking tables for daily limits

## Media Processing
- **OpenAI Integration**: Whisper API for audio transcription and GPT-4 mini for translations
- **FFmpeg**: Video processing to extract audio from video files
- **File Support**: Multiple audio formats (MP3, WAV, M4A, OGG, FLAC, AAC) and video formats (MP4, MOV, AVI, MKV, WebM)
- **File Size Limits**: 100MB maximum file size for processing

## Internationalization
- **Multi-language Support**: 12+ languages including English, Russian, Spanish, French, German, Italian, Portuguese, Chinese, Japanese, Korean, Arabic, and Hindi
- **Localized Messages**: Complete message localization system with language-specific user interfaces

## Business Model
- **Freemium Structure**: 1 free request per day for regular users
- **Premium Subscriptions**: Unlimited requests for 5 Telegram Stars per month
- **Usage Tracking**: Daily request counting and subscription status management

## Error Handling & Logging
- **Comprehensive Logging**: User action tracking, performance monitoring, and error reporting
- **Graceful Degradation**: File format validation, size checks, and processing error recovery

# External Dependencies

## Core Services
- **Telegram Bot API**: Primary platform for bot deployment and user interaction
- **OpenAI API**: Whisper for transcription and GPT-4 mini for translation services
- **PostgreSQL Database**: User data, subscription management, and usage analytics

## Media Processing
- **FFmpeg**: Video-to-audio conversion and media format handling
- **aiohttp**: Async HTTP client for downloading files from Telegram servers
- **aiofiles**: Async file operations for media processing

## Development Tools
- **python-dotenv**: Environment variable management
- **asyncio**: Asynchronous programming support for concurrent operations