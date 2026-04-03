import platform
import sys
import time
import asyncio
import requests
import re
from state import API_STATE, save_state
from datetime import timedelta
from telegram import Update
from telegram.ext import ContextTypes
from config import Config

# Record the start time when this module is loaded
START_TIME = time.time()

def check_service(url, timeout=5):
    """Pings a service to see if it's online."""
    try:
        # Standard user agent so we don't get accidentally blocked by basic bot protection
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, timeout=timeout, headers=headers)
        # Consider 200 (OK), 401 (Unauthorized, but API is up), and 403 (Forbidden, API is up) as 'Online' for ping purposes
        if response.status_code in [200, 401, 403]:
            return "🟢 Online"
        return f"🟡 HTTP {response.status_code}"
    except requests.exceptions.RequestException:
        return "🔴 Offline ⚠️"

async def toggle_api_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggles API state based on regex match."""
    # Security check: only the admin can toggle these
    if str(update.effective_user.id) != str(Config.ADMIN_ID):
        await update.message.reply_text(f"⛔ You are not authorized to use this command.\n\nYour ID is `{update.effective_user.id}`.\nPlease add `ADMIN_ID={update.effective_user.id}` to your `.env` file!", parse_mode="Markdown")
        return
        
    # text like: /debug_turn_groq_off
    text = update.message.text.lower()
    
    match = re.match(r"^/debug_turn_(groq|pollinations|daraz)_(on|off)", text)
    if not match:
        return
        
    api_name = match.group(1)
    action = match.group(2)
    
    # Update the global state
    is_on = True if action == "on" else False
    API_STATE[api_name] = is_on
    save_state()  # Persist to disk
    
    status_icon = "🟢" if is_on else "🔴"
    await update.message.reply_text(f"⚙️ {status_icon} Override: API **{api_name.capitalize()}** is now **{action.upper()}**.", parse_mode="Markdown")

async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command to show bot statistics, system info, and API status."""
    # Security check: only the admin can view debug
    if str(update.effective_user.id) != str(Config.ADMIN_ID):
        await update.message.reply_text(f"⛔ You are not authorized to use this command.\n\nYour ID is `{update.effective_user.id}`.\nPlease add `ADMIN_ID={update.effective_user.id}` to your `.env` file!", parse_mode="Markdown")
        return
        
    # Let the user know we're checking, because network requests take a moment
    status_msg = await update.message.reply_text("🔄 Pinging services and gathering stats...")
    
    # Calculate bot uptime
    uptime_seconds = int(time.time() - START_TIME)
    uptime_str = str(timedelta(seconds=uptime_seconds))
    
    # Get system info
    system_info = platform.system()
    release_info = platform.release()
    python_version = sys.version.split()[0]
    
    # Ping services asynchronously to not block our telegram event loop
    loop = asyncio.get_running_loop()
    
    if API_STATE["groq"]:
        groq_status = await loop.run_in_executor(None, check_service, "https://api.groq.com/openai/v1/models")
    else:
        groq_status = "🔴 Disabled (Admin)"
        
    if API_STATE["pollinations"]:
        pollinations_status = await loop.run_in_executor(None, check_service, "https://image.pollinations.ai/")
    else:
        pollinations_status = "🔴 Disabled (Admin)"
        
    if API_STATE["daraz"]:
        daraz_status = await loop.run_in_executor(None, check_service, "https://www.daraz.com.bd/")
    else:
        daraz_status = "🔴 Disabled (Admin)"
    
    # Format the message (using Markdown syntax supported by Telegram)
    debug_text = (
        "🛠️ *Bot Debug Info*\n\n"
        f"⏱️ *Uptime:* `{uptime_str}`\n"
        f"💻 *System:* `{system_info} {release_info}`\n"
        f"🐍 *Python:* `{python_version}`\n\n"
        "🌐 *API Health Status:*\n"
        f"🧠 *Groq AI:* {groq_status}\n"
        f"🎨 *Pollinations AI:* {pollinations_status}\n"
        f"🛒 *Daraz:* {daraz_status}"
    )
    
    # Edit our initial message with the final results
    await status_msg.edit_text(debug_text, parse_mode='Markdown')


