"""
Audio/Video processing module for transcription and translation
"""
import os
import tempfile
import asyncio
import aiofiles
import ffmpeg
from typing import Optional, Tuple
from openai import AsyncOpenAI
from bot.config import Config


class AudioProcessor:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
    
    async def download_file(self, file_path: str, file_url: str) -> Optional[str]:
        """Download file from Telegram servers"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    if response.status == 200:
                        async with aiofiles.open(file_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(1024):
                                await f.write(chunk)
                        return file_path
        except Exception as e:
            print(f"Error downloading file: {e}")
            return None
    
    def extract_audio_from_video(self, input_path: str, output_path: str) -> bool:
        """Extract audio from video file using ffmpeg"""
        try:
            (
                ffmpeg
                .input(input_path)
                .output(output_path, format='mp3', acodec='libmp3lame')
                .overwrite_output()
                .run(quiet=True)
            )
            return True
        except Exception as e:
            print(f"Error extracting audio: {e}")
            return False
    
    def get_file_format(self, filename: str) -> Tuple[str, bool]:
        """Determine file format and if it needs audio extraction"""
        ext = os.path.splitext(filename.lower())[1]
        
        if ext in Config.SUPPORTED_AUDIO_FORMATS:
            return "audio", False
        elif ext in Config.SUPPORTED_VIDEO_FORMATS:
            return "video", True
        else:
            return "unsupported", False
    
    async def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """Transcribe audio file using OpenAI Whisper"""
        try:
            with open(audio_path, 'rb') as audio_file:
                transcript = await self.openai_client.audio.transcriptions.create(
                    model=Config.WHISPER_MODEL,
                    file=audio_file,
                    response_format="text"
                )
            return transcript
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None
    
    async def translate_text(self, text: str, target_language: str, 
                            source_language: str = "auto") -> Optional[str]:
        """Translate text using OpenAI GPT"""
        try:
            if source_language == "auto":
                prompt = f"""Translate the following text to {target_language}. 
If the text is already in {target_language}, return it as is.

Text to translate:
{text}

Translation:"""
            else:
                prompt = f"""Translate the following text from {source_language} to {target_language}:

{text}

Translation:"""
            
            response = await self.openai_client.chat.completions.create(
                model=Config.GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional translator. Provide only the translation without any additional comments or explanations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error translating text: {e}")
            return None
    
    async def process_file(self, file_path: str, filename: str, 
                          target_language: str) -> Tuple[Optional[str], Optional[str], str]:
        """Process audio/video file: extract audio, transcribe, and translate"""
        file_type, needs_extraction = self.get_file_format(filename)
        
        if file_type == "unsupported":
            return None, None, "unsupported_format"
        
        audio_path = file_path
        temp_audio_path = None
        
        try:
            # Extract audio from video if needed
            if needs_extraction:
                temp_audio_path = f"{file_path}_audio.mp3"
                if not self.extract_audio_from_video(file_path, temp_audio_path):
                    return None, None, "extraction_failed"
                audio_path = temp_audio_path
            
            # Transcribe audio
            transcription = await self.transcribe_audio(audio_path)
            if not transcription:
                return None, None, "transcription_failed"
            
            # Translate transcription
            translation = await self.translate_text(transcription, target_language)
            if not translation:
                return transcription, None, "translation_failed"
            
            return transcription, translation, "success"
        
        except Exception as e:
            print(f"Error processing file: {e}")
            return None, None, "processing_error"
        
        finally:
            # Clean up temporary files
            try:
                if temp_audio_path and os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
            except:
                pass


# Global processor instance
audio_processor = AudioProcessor()