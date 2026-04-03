import os
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from services.tts import generate_speech
from utils.logger import get_logger

logger = get_logger(__name__)

async def say_command(update: Update, context: ContextTypes.DEFAULT_TYPE, voice_type: str = "male"):
    """
    Handler for /say and /say_as_girl commands.
    Generates and sends a voice message.
    """
    
    # 1. Check for text input
    if not context.args:
        help_text = (
            "🎙️ **Text to Speech**\n\n"
            "Usage:\n"
            "👨 `/say [text]` — Male Voice\n"
            "👩 `/say_as_girl [text]` — Female Voice\n\n"
            "Example: `/say_as_girl আমার নাম লুসিফার`"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")
        return

    text = " ".join(context.args)
    
    # Show "Recording" action to the user
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
    
    try:
        # 2. Generate Audio
        audio_path = await generate_speech(text, voice_type)
        
        # 3. Send Voice Message
        # We use voice message (.ogg) for the best Telegram experience
        with open(audio_path, 'rb') as voice:
            await update.message.reply_voice(
                voice=voice,
                caption=f"🎙️ *Prompt:* {text[:60]}{'...' if len(text) > 60 else ''}",
                parse_mode="Markdown"
            )
            
        # 4. Clean Up
        # Small delay to ensure the file is closed on Windows
        await asyncio.sleep(0.1)
        os.remove(audio_path)
        
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        await update.message.reply_text(f"❌ Failed to generate speech.\n\n**Reason:** `{e}`", parse_mode="Markdown")

async def say_male_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Specific wrapper for /say (Male)"""
    await say_command(update, context, "male")

async def say_female_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Specific wrapper for /say_as_girl (Female)"""
    await say_command(update, context, "female")
