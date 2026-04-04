import platform
import sys
import time
import asyncio
import requests
import re
from state import API_STATE, save_state, get_stats_summary
from datetime import timedelta
from telegram import Update
from telegram.ext import ContextTypes
from config import Config

# Record the start time when this module is loaded
START_TIME = time.time()


def check_service(url, timeout=5):
    """Pings a service to see if it's online."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, timeout=timeout, headers=headers)
        if response.status_code in [200, 401, 403]:
            return "🟢 Online"
        return f"🟡 HTTP {response.status_code}"
    except requests.exceptions.RequestException:
        return "🔴 Offline ⚠️"


async def toggle_api_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggles API state based on regex match."""
    if str(update.effective_user.id) != str(Config.ADMIN_ID):
        await update.message.reply_text(
            f"⛔ You are not authorized.\n\n"
            f"Your ID: <code>{update.effective_user.id}</code>.\n"
            f"Add <code>ADMIN_ID={update.effective_user.id}</code> to <code>.env</code>!",
            parse_mode="HTML",
        )
        return

    text = update.message.text.lower()
    match = re.match(r"^/debug_turn_(groq|pollinations|daraz)_(on|off)", text)
    if not match:
        return

    api_name = match.group(1)
    action = match.group(2)
    is_on = action == "on"
    API_STATE[api_name] = is_on
    save_state()

    status_icon = "🟢" if is_on else "🔴"
    await update.message.reply_text(
        f"⚙️ {status_icon} Override: API <b>{api_name.capitalize()}</b> is now <b>{action.upper()}</b>.",
        parse_mode="HTML",
    )


async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command to show bot statistics, system info, and API status."""
    if str(update.effective_user.id) != str(Config.ADMIN_ID):
        await update.message.reply_text(
            f"⛔ You are not authorized.\n\n"
            f"Your ID: <code>{update.effective_user.id}</code>.\n"
            f"Add <code>ADMIN_ID={update.effective_user.id}</code> to <code>.env</code>!",
            parse_mode="HTML",
        )
        return

    status_msg = await update.message.reply_text("🔄 Pinging services and gathering stats...")

    # Uptime
    uptime_seconds = int(time.time() - START_TIME)
    uptime_str = str(timedelta(seconds=uptime_seconds))

    # System info
    system_info = platform.system()
    release_info = platform.release()
    python_version = sys.version.split()[0]

    # Ping services in PARALLEL (much faster than sequential)
    loop = asyncio.get_running_loop()
    tasks = {}

    if API_STATE["groq"]:
        tasks["groq"] = loop.run_in_executor(None, check_service, "https://api.groq.com/openai/v1/models")
    if API_STATE["pollinations"]:
        tasks["pollinations"] = loop.run_in_executor(None, check_service, "https://image.pollinations.ai/")
    if API_STATE["daraz"]:
        tasks["daraz"] = loop.run_in_executor(None, check_service, "https://www.daraz.com.bd/")

    # Await all pings simultaneously
    results = {}
    if tasks:
        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for key, result in zip(tasks.keys(), gathered):
            results[key] = result if not isinstance(result, Exception) else "🔴 Error"

    groq_status = results.get("groq", "🔴 Disabled (Admin)")
    pollinations_status = results.get("pollinations", "🔴 Disabled (Admin)")
    daraz_status = results.get("daraz", "🔴 Disabled (Admin)")

    # User statistics
    stats = get_stats_summary()

    # Save state to persist stats
    save_state()

    debug_text = (
        "🛠️ <b>Bot Debug Info</b>\n\n"
        f"⏱️ <b>Uptime:</b> <code>{uptime_str}</code>\n"
        f"💻 <b>System:</b> <code>{system_info} {release_info}</code>\n"
        f"🐍 <b>Python:</b> <code>{python_version}</code>\n\n"
        "📈 <b>User Statistics:</b>\n"
        f"{stats}\n\n"
        "🌐 <b>API Health Status:</b>\n"
        f"🧠 <b>Groq AI:</b> {groq_status}\n"
        f"🎨 <b>Pollinations AI:</b> {pollinations_status}\n"
        f"🛒 <b>Daraz:</b> {daraz_status}"
    )

    await status_msg.edit_text(debug_text, parse_mode="HTML")
