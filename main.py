import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from config import Config
from handlers.basic import start_command, handle_message, button_callback, back_to_start_callback, help_command, clear_history_command
from handlers.image_gen import generate_image_command
from handlers.daraz_handler import find_deal_command
from handlers.weather import weather_command
from handlers.tts import say_male_command, say_female_command
from handlers.debug import debug_command, toggle_api_command, what_type_command
from handlers.persona import persona_command, persona_callback
from handlers.translate import translate_command
from handlers.voice_input import handle_voice_message
from handlers.qr import qr_command
from handlers.currency import convert_command
from handlers.quiz import quiz_command, quiz_answer_callback
from handlers.ocr import ocr_command
from handlers.download import download_command, download_callback
from handlers.news import news_command
from handlers.sticker import sticker_command
from handlers.games import play_command, stopgame_command, game_callback
from handlers.profile import profile_command
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# Health Check Server (Required for Koyeb / Cloud Hosting)
# ============================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    """Responds to any request with 200 OK."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Lucifer Bot is running!")

    def log_message(self, format, *args):
        pass


def start_health_server():
    """Starts the health check server in a background daemon thread."""
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"Health check server started on port {port}")
    server.serve_forever()


# ============================================================
# Global Error Handler
# ============================================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Catches unhandled exceptions from any handler and notifies the user."""
    logger.error(f"Unhandled exception: {context.error}", exc_info=context.error)
    
    # Try to notify the user if possible
    if update and isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "😔 Something went wrong while processing your request. Please try again."
            )
        except Exception:
            pass  # If even this fails, just log it


async def post_init(application: Application):
    """Sets the Telegram Menu button commands with bilingual descriptions."""
    commands = [
        ("start", "🏠 শুরু | Start Bot"),
        ("image", "🎨 ভাবো | AI Art"),
        ("find", "🛒 খুঁজো | Find Deals"),
        ("weather", "🌤️ আবহাওয়া | Weather"),
        ("say", "👨 বলো | Boy Voice"),
        ("say_as_girl", "👩 মেয়ের মত বলো | Girl Voice"),
        ("translate", "🌐 অনুবাদ | Translate"),
        ("convert", "💱 রূপান্তর | Currency"),
        ("qr", "📱 QR Code"),
        ("quiz", "🧩 কুইজ | Quiz"),
        ("ocr", "📄 OCR | Text Extract"),
        ("sticker", "🖼️ স্টিকার | Sticker Maker"),
        ("news", "📰 খবর | Daily News"),
        ("persona", "🎭 ব্যক্তিত্ব | AI Persona"),
        ("download", "📥 ডাউনলোড | Download Media"),
        ("play", "🎲 খেলো | Interactive Games"),
        ("me", "📊 প্রোফাইল | My Profile"),
        ("clear", "🗑️ মুছো | Clear History"),
        ("help", "❓ সাহায্য | Help"),
    ]
    await application.bot.set_my_commands(commands)


def main():
    if not Config.TELEGRAM_TOKEN:
        logger.error("No token found in .env file!")
        return

    # Start the health check server in a background thread (for Koyeb)
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()

    # Build the application and include the Menu setup
    app = Application.builder().token(Config.TELEGRAM_TOKEN).post_init(post_init).build()

    import re

    def create_universal_handler(commands: list, func):
        """
        Creates a handler that catches /command, /bangla_command, and @botname /command.
        Automatically fixes context.args so the original functions work perfectly.
        """
        pattern = r"^(?:@\w+\s+)?/(" + "|".join(commands) + r")(?:\s+|$)"
        
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if context.args is None:
                text = update.message.text or update.message.caption or ""
                # Strip @botname if present
                clean_text = re.sub(r"^@\w+\s+", "", text)
                # Populate args identically to CommandHandler
                context.args = clean_text.split()[1:]
            return await func(update, context)
            
        return MessageHandler(filters.Regex(pattern), wrapper)

    # --- 1 & 2. Universal Bilingual Command Handlers ---
    app.add_handler(create_universal_handler(["start", "শুরু"], start_command))
    app.add_handler(create_universal_handler(["help", "সাহায্য"], help_command))
    app.add_handler(create_universal_handler(["image", "ভাবো"], generate_image_command))
    app.add_handler(create_universal_handler(["find", "খুঁজো"], find_deal_command))
    app.add_handler(create_universal_handler(["weather", "আবহাওয়া"], weather_command))
    app.add_handler(create_universal_handler(["say", "বলো"], say_male_command))
    app.add_handler(create_universal_handler(["say_as_girl", "মেয়ের_মত_বলো"], say_female_command))
    app.add_handler(create_universal_handler(["translate", "অনুবাদ"], translate_command))
    app.add_handler(create_universal_handler(["convert", "রূপান্তর"], convert_command))
    app.add_handler(create_universal_handler(["qr", "কিউআর"], qr_command))
    app.add_handler(create_universal_handler(["quiz", "কুইজ"], quiz_command))
    app.add_handler(create_universal_handler(["ocr", "ওসিআর"], ocr_command))
    app.add_handler(create_universal_handler(["sticker", "স্টিকার"], sticker_command))
    app.add_handler(create_universal_handler(["news", "খবর"], news_command))
    app.add_handler(create_universal_handler(["persona", "ব্যক্তিত্ব"], persona_command))
    app.add_handler(create_universal_handler(["download", "ডাউনলোড"], download_command))
    app.add_handler(create_universal_handler(["play", "খেলো"], play_command))
    app.add_handler(create_universal_handler(["stopgame", "থামো"], stopgame_command))
    app.add_handler(create_universal_handler(["me", "আমি"], profile_command))
    app.add_handler(create_universal_handler(["clear", "মুছো"], clear_history_command))

    # --- 3. UI & Callback Handlers ---
    # Persona callback (must come before the generic button_callback)
    app.add_handler(CallbackQueryHandler(persona_callback, pattern=r"^persona_"))
    # Games callback
    app.add_handler(CallbackQueryHandler(game_callback, pattern=r"^game_"))
    # Quiz answer callback
    app.add_handler(CallbackQueryHandler(quiz_answer_callback, pattern=r"^quiz_"))
    # Download quality selection callback
    app.add_handler(CallbackQueryHandler(download_callback, pattern=r"^dl_"))
    # Back to menu callback
    app.add_handler(CallbackQueryHandler(back_to_start_callback, pattern=r"^back_to_start$"))
    # Generic help button callback
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"^help_"))

    # --- 4. Voice Message Handler ---
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_message))

    # --- 5. Standard AI Message Handler (text + photos) ---
    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.PHOTO) & ~filters.COMMAND & ~filters.Regex(r"^/"),
            handle_message,
        )
    )

    # --- 6. Admin Debug Commands ---
    app.add_handler(CommandHandler("debug", debug_command))
    app.add_handler(CommandHandler("what_type", what_type_command))
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^/debug_turn_(groq|pollinations|daraz)_(on|off)"),
            toggle_api_command,
        )
    )

    # --- 7. Global Error Handler ---
    app.add_error_handler(error_handler)

    logger.info("Lucifer is starting...")
    app.run_polling()


if __name__ == "__main__":
    main()