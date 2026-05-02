import asyncio
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.ai_chat import get_ai_response, get_ai_response_stream
from state import API_STATE, track_user, track_command
from utils.logger import get_logger
from utils.format import prepare_telegram_html, clean_markdown_fallback
from utils.constants import MAX_HISTORY, DEVELOPER_NAME, GITHUB_URL, ASSET_PROFILE_PICTURE
from utils.decorators import enforce_moderation
from handlers.intent import detect_intent
from handlers.reminder import handle_reminder_text

logger = get_logger(__name__)


# ── Categorized Start Menu Builder ───────────────────────────
def _build_start_menu(user_first_name: str):
    """
    Categorized welcome menu — clean, organized, easy to navigate.
    Only shows 6 category buttons instead of overwhelming with all features.
    """
    welcome_text = (
        f"👋 <b>Hi {user_first_name}! I am Lucifer.</b>\n"
        "আমি তোমার গ্রুপের AI সহকারী 🤖\n\n"
        "💬 <b>Just type to chat with me!</b>\n"
        "Or pick a category below to explore:\n"
    )

    keyboard = [
        [
            InlineKeyboardButton("🤖 AI Tools", callback_data="cat_ai"),
            InlineKeyboardButton("🛠️ Utilities", callback_data="cat_utils"),
        ],
        [
            InlineKeyboardButton("🎮 Games & Fun", callback_data="cat_fun"),
            InlineKeyboardButton("📱 Local BD", callback_data="cat_local"),
        ],
        [
            InlineKeyboardButton("⏰ Productivity", callback_data="cat_prod"),
            InlineKeyboardButton("📊 Profile", callback_data="cat_profile"),
        ],
        [
            InlineKeyboardButton("👨‍💻 Developer & Credits", callback_data="developer_info"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return welcome_text, reply_markup


# ── Category Content Definitions ─────────────────────────────
CATEGORY_CONTENT = {
    "cat_ai": {
        "title": "🤖 <b>AI Tools</b>",
        "desc": "Intelligent AI-powered features",
        "buttons": [
            ("🎨 AI Art Generator", "/image "),
            ("🎭 AI Persona Switch", "/persona "),
            ("💡 Explain (Reply)", "/explain"),
            ("📋 Summarize (Reply)", "/summarize"),
            ("✍️ Rewrite (Reply)", "/rewrite"),
            ("📄 OCR Text Extract", "/ocr"),
            ("🖼️ Sticker Maker", "/sticker "),
        ],
    },
    "cat_utils": {
        "title": "🛠️ <b>Utilities</b>",
        "desc": "Useful everyday tools",
        "buttons": [
            ("🌤️ Weather", "/weather Dhaka"),
            ("💱 Currency Convert", "/convert "),
            ("🇺🇸🇧🇩 USD→BDT Rate", "/bdt "),
            ("🌐 Translate", "/translate "),
            ("🎙️ TTS Male Voice", "/say "),
            ("👩 TTS Female Voice", "/say_as_girl "),
            ("📱 QR Code", "/qr "),
            ("📥 Download Media", "/download "),
        ],
    },
    "cat_fun": {
        "title": "🎮 <b>Games & Fun</b>",
        "desc": "Play games and challenge yourself",
        "buttons": [
            ("🎲 Play Games", "/play"),
            ("🧩 AI Quiz", "/quiz "),
            ("🗳️ Quick Vote", "/vote "),
            ("📊 Create Poll", "/poll "),
        ],
    },
    "cat_local": {
        "title": "📱 <b>Local Bangladesh</b>",
        "desc": "Bangladesh-focused tools & info",
        "buttons": [
            ("📰 News Headlines", "/news "),
            ("🇧🇩 BD News", "/news bd"),
            ("🛒 Daraz Deals", "/find "),
            ("🕌 Prayer Times", "/prayer"),
            ("📱 Mobile Offers", "/offers"),
        ],
    },
    "cat_prod": {
        "title": "⏰ <b>Productivity</b>",
        "desc": "Stay organized and on track",
        "buttons": [
            ("⏰ Set Reminder", "/remind"),
            ("📋 My Reminders", "/myreminders"),
            ("🗑️ Clear History", "/clear"),
        ],
    },
    "cat_profile": {
        "title": "📊 <b>Your Profile</b>",
        "desc": "Stats, persona, and settings",
        "buttons": [
            ("📊 My Profile", "/me"),
            ("🎭 Switch Persona", "/persona"),
            ("🗑️ Clear History", "/clear"),
        ],
    },
}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rich Welcome message with Branding Photo for Lucifer."""
    user = update.effective_user
    track_user(user.id)
    track_command("start")

    welcome_text, reply_markup = _build_start_menu(user.first_name)

    # Resolve character limit for photo captions (default is 1024)
    # Our welcome_text is well under that limit.
    
    photo_path = os.path.join(os.getcwd(), ASSET_PROFILE_PICTURE)
    
    if os.path.exists(photo_path):
        with open(photo_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=welcome_text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
    else:
        # Fallback to text only if the image is missing
        await update.message.reply_text(
            text=welcome_text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )


@enforce_moderation()
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main message handler — checks reminder flow, intent detection, then AI chat."""
    
    # ── Step 0: Check if user is in reminder text input mode ──
    if update.message.text and await handle_reminder_text(update, context):
        return

    if not API_STATE.get("groq", True):
        await update.message.reply_text(
            "🤖 Groq AI Chat is currently disabled by the Admin. Please try again later."
        )
        return

    if not FEATURE_FLAGS.get("ai_chat", True):
        await update.message.reply_text(
            "💬 AI Chat is currently disabled by the Admin. Please try again later."
        )
        return

    track_command("ai_chat")

    image_bytes = None
    if update.message.photo:
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        image_bytes = await photo_file.download_as_bytearray()

    user_text = update.message.caption if update.message.photo else update.message.text

    if not user_text and image_bytes:
        user_text = "Please analyze this image."

    # ── Group Chat Handling ──
    is_group = update.effective_chat.type in ["group", "supergroup"]
    if is_group:
        bot_username = context.bot.username
        is_reply_to_bot = (
            update.message.reply_to_message 
            and update.message.reply_to_message.from_user.id == context.bot.id
        )
        is_mentioned = user_text and f"@{bot_username}" in user_text

        # If it's a group and we aren't mentioned or replied to, ignore it so we don't spam
        if not (is_reply_to_bot or is_mentioned):
            return
        
        # Clean up the mention from the text so the AI doesn't get confused
        if is_mentioned:
            user_text = user_text.replace(f"@{bot_username}", "").strip()
            if not user_text and not image_bytes:
                user_text = "Hello!"

    # ── Step 1: Natural Language Intent Detection ──
    # Only for text messages (not images), try to match known intents
    if user_text and not image_bytes:
        intent, intent_args = detect_intent(user_text)
        if intent:
            await _dispatch_intent(update, context, intent, intent_args)
            return

    # Typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Get chat history and persona/game state
    chat_history = context.user_data.get("chat_history", [])
    persona = context.user_data.get("persona", "default")
    active_game = context.user_data.get("active_game")
    
    point_awarded_this_turn = False

    # ── IMAGE PATH: Non-streaming (Vision doesn't support streaming) ──
    if image_bytes:
        sent_message = await update.message.reply_text("🤔 Analyzing image...")
        response = await get_ai_response(
            user_text,
            image_bytes=image_bytes,
            chat_history=chat_history[-MAX_HISTORY:],
            persona=persona,
            game_mode=active_game,
        )
        
        # Point checking for non-streaming (image vision usually won't trigger games, but safe to check)
        if "[POINT_AWARDED]" in response:
            point_awarded_this_turn = True
            response = response.replace("[POINT_AWARDED]", "").strip()
            
        display_text = response
        if point_awarded_this_turn:
            display_text += "\n\n🎉 <b>You earned a point!</b>"
            
        try:
            await sent_message.edit_text(prepare_telegram_html(display_text), parse_mode="HTML")
        except Exception:
            try:
                await sent_message.edit_text(clean_markdown_fallback(display_text))
            except Exception:
                pass
    else:
        # ── TEXT PATH: Streaming response ──
        sent_message = await update.message.reply_text("🤔 Thinking...")
        
        accumulated = ""
        current_offset = 0
        last_edit = ""
        last_update_time = time.time()

        try:
            async for chunk in get_ai_response_stream(
                user_text,
                chat_history=chat_history[-MAX_HISTORY:],
                persona=persona,
                game_mode=active_game,
            ):
                accumulated += chunk
                
                # Check for hidden points
                if "[POINT_AWARDED]" in accumulated and not point_awarded_this_turn:
                    point_awarded_this_turn = True
                    # Initialize points if missing
                    context.user_data["game_points"] = context.user_data.get("game_points", 0) + 1

                # Paginate if the text exceeds Telegram's 4096 limit
                current_segment = accumulated[current_offset:]
                if len(current_segment) > 4000:
                    # Finalize the current message
                    last_space = current_segment.rfind(' ')
                    if last_space == -1: 
                        last_space = 4000
                        
                    final_segment = current_segment[:last_space].replace("[POINT_AWARDED]", "").strip()
                    try:
                        await sent_message.edit_text(prepare_telegram_html(final_segment), parse_mode="HTML")
                    except Exception:
                        try:
                            await sent_message.edit_text(clean_markdown_fallback(final_segment))
                        except Exception:
                            pass
                            
                    # Create a new overflow message
                    current_offset += last_space
                    current_segment = accumulated[current_offset:]
                    sent_message = await update.message.reply_text("...")
                    last_edit = ""
                    last_update_time = time.time()

                # Time-based update to perfectly dodge Telegram rate limits (approx 1 update per 0.5s-1s)
                current_time = time.time()
                if (current_time - last_update_time) > 0.8 and current_segment != last_edit:
                    display_text = current_segment.replace("[POINT_AWARDED]", "").strip()
                    if point_awarded_this_turn and current_offset == 0:  # Only show point popup if on first paginated chunk
                        display_text += "\n\n🎉 <b>You earned a point!</b>"

                    try:
                        last_edit = current_segment
                        last_update_time = current_time
                        await sent_message.edit_text(display_text + " ▌")
                    except Exception as e:
                        # Log but do not crash. If it's 400 Message is not modified, it's safe to ignore.
                        if "not modified" not in str(e).lower():
                            logger.error(f"Stream edit error: {e}")

            # Final edit with complete response (remove cursor)
            if accumulated:
                response = accumulated
                final_segment = accumulated[current_offset:]
                display_text = final_segment.replace("[POINT_AWARDED]", "").strip()
                if point_awarded_this_turn and current_offset == 0:
                    display_text += f"\n\n🎉 <b>You earned a point!</b> (Total Points: {context.user_data.get('game_points', 0)})"
            else:
                response = "🤔 I couldn't generate a response. Please try again."
                display_text = response

            try:
                await sent_message.edit_text(prepare_telegram_html(display_text), parse_mode="HTML")
            except Exception:
                try:
                    await sent_message.edit_text(clean_markdown_fallback(display_text))
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            response = f"🔧 Error: {str(e)}"
            await sent_message.edit_text(response)

    # Update conversation memory ONLY if it wasn't an API crash
    if not response.startswith("🔧 Error:") and not response.startswith("❌ All Chat models are currently down") and "Request too large" not in response:
        chat_history.append({"role": "user", "content": user_text})
        chat_history.append({"role": "assistant", "content": response})
        context.user_data["chat_history"] = chat_history[-MAX_HISTORY:]


async def clear_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear the user's conversation history."""
    context.user_data.pop("chat_history", None)
    context.user_data.pop("quiz_score", None)
    context.user_data.pop("quiz_total", None)
    track_command("clear")

    await update.message.reply_text(
        "🗑️ Conversation history cleared!\n\n"
        "I've forgotten our previous chat. Start fresh! 🚀"
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle help button clicks from the inline keyboard."""
    query = update.callback_query
    await query.answer()

    HELP_MESSAGES = {
        "help_main": (
            "📜 <b>All Commands</b>\n\n"
            "<b>🤖 AI:</b>\n"
            "• <code>/image</code> — Art Gen\n"
            "• <code>/persona</code> — AI Style\n"
            "• <code>/explain</code> — Explain (reply)\n"
            "• <code>/summarize</code> — Summarize (reply)\n"
            "• <code>/rewrite</code> — Rewrite (reply)\n\n"
            "<b>🛠️ Utils:</b>\n"
            "• <code>/weather</code> — Weather\n"
            "• <code>/convert</code> — Currency\n"
            "• <code>/bdt</code> — Quick USD→BDT\n"
            "• <code>/translate</code> — Translate\n"
            "• <code>/say</code> / <code>/say_as_girl</code> — TTS\n"
            "• <code>/qr</code> — QR Code\n"
            "• <code>/download</code> — Media DL\n"
            "• <code>/ocr</code> — Text Extract\n"
            "• <code>/sticker</code> — Sticker Maker\n\n"
            "<b>🎮 Games:</b>\n"
            "• <code>/play</code> — AI Games\n"
            "• <code>/quiz</code> — Trivia\n"
            "• <code>/vote</code> — Quick Vote\n"
            "• <code>/poll</code> — Group Poll\n\n"
            "<b>📱 Local BD:</b>\n"
            "• <code>/news</code> — Headlines\n"
            "• <code>/find</code> — Daraz Deals\n"
            "• <code>/prayer</code> — Prayer Times\n"
            "• <code>/offers</code> — Mobile Offers\n\n"
            "<b>⏰ Productivity:</b>\n"
            "• <code>/remind</code> — Set Reminder\n"
            "• <code>/myreminders</code> — My Reminders\n\n"
            "<b>📊 Profile:</b>\n"
            "• <code>/me</code> — Stats\n"
            "• <code>/clear</code> — Reset Memory"
        ),
    }

    message = HELP_MESSAGES.get(query.data, "Unknown action.")

    back_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 মেনুতে ফিরুন | Back to Menu", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text=message, parse_mode="HTML", reply_markup=back_button)


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category navigation button clicks from the /start menu."""
    query = update.callback_query
    await query.answer()

    cat_key = query.data  # e.g. "cat_ai"
    cat = CATEGORY_CONTENT.get(cat_key)

    if not cat:
        await query.edit_message_text("❌ Unknown category.")
        return

    text = f"{cat['title']}\n{cat['desc']}\n\n<i>Click a feature to use it:</i>"

    keyboard = []
    for label, cmd in cat["buttons"]:
        keyboard.append([InlineKeyboardButton(label, switch_inline_query_current_chat=cmd)])

    keyboard.append([
        InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_start"),
        InlineKeyboardButton("📜 All Commands", callback_data="help_main"),
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Edit caption if it's a photo message, otherwise edit text
    if query.message.photo:
        await query.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="HTML")


async def back_to_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Back to Menu' button — rebuild the /start menu with photo."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    welcome_text, reply_markup = _build_start_menu(user.first_name)
    
    photo_path = os.path.join(os.getcwd(), ASSET_PROFILE_PICTURE)

    if os.path.exists(photo_path):
        # We delete the old message and send a new one to show the photo correctly
        # This keeps the flow clean and premium.
        try:
            await query.message.delete()
        except:
            pass # Old message might have been deleted already
            
        with open(photo_path, 'rb') as photo:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo,
                caption=welcome_text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
    else:
        await query.edit_message_text(
            text=welcome_text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )

async def developer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show developer info and GitHub link."""
    query = update.callback_query
    await query.answer()
    
    dev_text = (
        f"👨‍💻 <b>Developer Profile</b>\n\n"
        f"<b>Name:</b> {DEVELOPER_NAME}\n"
        f"<b>Role:</b> Lead Architect & Developer\n\n"
        "Thank you for using Lucifer! This project is a labor of love dedicated to building "
        "the most intelligent and accessible AI companion for everyone.\n\n"
        "🚀 <b>Open Source:</b>\n"
        "Support the development by checking out the source code on GitHub. "
        "Leave a star if you like this project! ⭐\n\n"
        f"🔗 <a href='{GITHUB_URL}'>Visit Shariar's GitHub Profile</a>"
    )
    
    keyboard = [
        [InlineKeyboardButton("⭐ Follow on GitHub", url=GITHUB_URL)],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Developers like a clean UI, so we edit the text (or caption if it's a photo)
    if query.message.photo:
        await query.message.edit_caption(caption=dev_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await query.edit_message_text(text=dev_text, reply_markup=reply_markup, parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple help fallback — redirects to /start."""
    await update.message.reply_text("Use /start to see the full menu with all features!")


# ── Intent Dispatcher ────────────────────────────────────────
async def _dispatch_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, intent: str, args: str):
    """Dispatch a detected intent to the appropriate handler."""
    # Import handlers lazily to avoid circular imports
    from handlers.weather import weather_command
    from handlers.currency import convert_command, bdt_command
    from handlers.news import news_command
    from handlers.reminder import remind_command
    from handlers.prayer import prayer_command
    from handlers.mobile import mobile_command
    from handlers.vote import vote_command

    # Simulate context.args from extracted intent args
    context.args = args.split() if args else []

    intent_map = {
        "weather": weather_command,
        "weather_no_args": weather_command,
        "bdt_rate": bdt_command,
        "convert": convert_command,
        "news": news_command,
        "reminder": remind_command,
        "prayer": prayer_command,
        "mobile_offer": mobile_command,
        "vote": vote_command,
    }

    handler = intent_map.get(intent)
    if handler:
        await handler(update, context)
    else:
        logger.warning(f"Intent '{intent}' matched but no handler mapped.")