import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from services.weather import get_weather
from utils.logger import get_logger

logger = get_logger(__name__)

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /weather command."""
    if not context.args:
        await update.message.reply_text("🌤️ Please provide a city name. Example: `/weather Dhaka`", parse_mode="Markdown")
        return

    city = " ".join(context.args)
    status_msg = await update.message.reply_text(f"🔍 Checking weather for '{city}'...")

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, get_weather, city)

    if result.get("success"):
        weather_text = (
            f"🌍 **Weather in {result['city']}, {result['country']}**\n\n"
            f"🌡️ **Temperature:** {result['temp']}°C\n"
            f"☁️ **Condition:** {result['description']}"
        )
        await status_msg.edit_text(weather_text, parse_mode="Markdown")
    else:
        await status_msg.edit_text(f"❌ Could not fetch weather.\n\n**Reason:** {result.get('error')}", parse_mode="Markdown")
