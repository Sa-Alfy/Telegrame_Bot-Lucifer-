import time
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from state import API_STATE


def rate_limit(seconds: int = 15):
    """
    Decorator: Per-user cooldown to prevent spamming expensive API calls.
    Usage: @rate_limit(seconds=30)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            key = f"_cooldown_{func.__name__}"
            
            last_used = context.user_data.get(key, 0)
            now = time.time()
            remaining = seconds - (now - last_used)
            
            if remaining > 0:
                await update.message.reply_text(
                    f"⏳ Please wait **{int(remaining)}s** before using this again.",
                    parse_mode="Markdown"
                )
                return
            
            context.user_data[key] = now
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator


def require_args(help_message: str):
    """
    Decorator: Auto-reply with help text if no arguments are provided.
    Usage: @require_args("Please provide a prompt! Example: /image sunset")
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if not context.args:
                await update.message.reply_text(help_message, parse_mode="Markdown")
                return
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator


def api_enabled(api_name: str):
    """
    Decorator: Check if an API is enabled in global state before running.
    Usage: @api_enabled("groq")
    """
    FRIENDLY_NAMES = {
        "groq": "🤖 AI Chat",
        "pollinations": "🎨 Image Generation",
        "daraz": "🛒 Daraz Deal Finder",
    }
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if not API_STATE.get(api_name, True):
                name = FRIENDLY_NAMES.get(api_name, api_name.capitalize())
                await update.message.reply_text(
                    f"{name} is currently disabled by the Admin. Please try again later."
                )
                return
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator
