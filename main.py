import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import Config
from handlers.basic import start_command, handle_message, button_callback
from handlers.image_gen import generate_image_command
from handlers.daraz_handler import find_deal_command
from handlers.weather import weather_command
from handlers.debug import debug_command, toggle_api_command
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# Health Check Server (Required for Koyeb / Cloud Hosting)
# This tiny server runs in the background and just replies "OK"
# so the hosting platform knows our bot is alive.
# It does NOT affect the Telegram bot in any way.
# ============================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    """Responds to any request with 200 OK."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Lucifer Bot is running!")

    def log_message(self, format, *args):
        # Silence health-check logs to keep console clean
        pass

def start_health_server():
    """Starts the health check server in a background daemon thread."""
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"Health check server started on port {port}")
    server.serve_forever()


async def post_init(application: Application):
    """
    This function sets up the 'Menu' button in the Telegram UI 
    so users always see available commands.
    """
    commands = [
        ("start", "🏠 Open Main Menu"),
        ("image", "🎨 Generate AI Art"),
        ("find", "🛒 Find Daraz Deals"),
        ("weather", "🌤️ Check Weather"),
    ]
    await application.bot.set_my_commands(commands)

def main():
    # Use the token from our Config class
    if not Config.TELEGRAM_TOKEN:
        logger.error("No token found in .env file!")
        return

    # Start the health check server in a background thread (for Koyeb)
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()

    # Build the application and include the Menu setup
    app = Application.builder().token(Config.TELEGRAM_TOKEN).post_init(post_init).build()

    # 1. Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("image", generate_image_command))
    app.add_handler(CommandHandler("find", find_deal_command))
    app.add_handler(CommandHandler("weather", weather_command))

    # 2. Button Click Handler
    app.add_handler(CallbackQueryHandler(button_callback))

    # 3. Handle standard AI messages (including photos for Vision!)
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))

    # 4. Admin Debug Commands
    app.add_handler(CommandHandler("debug", debug_command))
    app.add_handler(MessageHandler(filters.Regex(r'^/debug_turn_(groq|pollinations|daraz)_(on|off)'), toggle_api_command))

    logger.info("Lucifer is starting...")
    # Run the bot
    app.run_polling()

if __name__ == '__main__':
    main()