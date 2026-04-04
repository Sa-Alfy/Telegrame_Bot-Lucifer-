import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.ai_chat import get_ai_response, get_ai_response_stream
from state import API_STATE, track_user, track_command
from utils.logger import get_logger
from utils.format import prepare_telegram_html, clean_markdown_fallback
from utils.constants import MAX_HISTORY

logger = get_logger(__name__)


# ── Shared Start Menu Builder ────────────────────────────────
def _build_start_menu(user_first_name: str):
    """
    Single source of truth for the /start welcome text and keyboard.
    Used by both start_command() and back_to_start_callback().
    """
    welcome_text = (
        f"👋 <b>Hi {user_first_name}! I am the Shariar Tech Bot.</b>\n"
        "আমি একটি মাল্টি-ফাংশনাল এআই সহকারী।\n\n"
        "🚀 <b>My Features (আমার কাজ):</b>\n"
        "🤖 <b>AI Chat:</b> Just talk to me!\n"
        "🎨 <b>AI Art:</b> <code>/image</code> — generate images\n"
        "🛒 <b>Deals:</b> <code>/find</code> — search Daraz\n"
        "🎙️ <b>Voice:</b> <code>/say</code> — text to speech\n"
        "🌐 <b>Translate:</b> <code>/translate</code> — Any language\n"
        "💱 <b>Currency:</b> <code>/convert</code> — convert money\n"
        "📱 <b>QR Code:</b> <code>/qr</code> — generate QR codes\n"
        "🧩 <b>Quiz:</b> <code>/quiz</code> — trivia game\n"
        "📄 <b>OCR:</b> <code>/ocr</code> — extract text from images\n"
        "📥 <b>Download:</b> <code>/download</code> — download media\n"
        "🎭 <b>Persona:</b> <code>/persona</code> — change AI style\n"
        "🎤 <b>Voice Chat:</b> Send voice messages!\n"
        "📊 <b>Profile:</b> <code>/me</code> — your stats\n\n"
        "👇 <b>Quick Actions (দ্রুত কাজ):</b>"
    )

    keyboard = [
        [
            InlineKeyboardButton("🎨 ভাবো | Art", callback_data="help_image"),
            InlineKeyboardButton("🛒 খুঁজো | Deals", callback_data="help_find"),
        ],
        [
            InlineKeyboardButton("🎙️ বলো | Voice", callback_data="help_tts"),
            InlineKeyboardButton("🌤️ আবহাওয়া | Weather", callback_data="help_weather"),
        ],
        [
            InlineKeyboardButton("🌐 Translate", callback_data="help_translate"),
            InlineKeyboardButton("💱 Currency", callback_data="help_currency"),
        ],
        [
            InlineKeyboardButton("📱 QR Code", callback_data="help_qr"),
            InlineKeyboardButton("🧩 Quiz", callback_data="help_quiz"),
        ],
        [
            InlineKeyboardButton("🎭 Persona", callback_data="help_persona"),
            InlineKeyboardButton("📄 OCR", callback_data="help_ocr"),
        ],
        [
            InlineKeyboardButton("📰 News", callback_data="help_news"),
            InlineKeyboardButton("🖼️ Sticker Maker", callback_data="help_sticker"),
        ],
        [
            InlineKeyboardButton("📥 Download", callback_data="help_download"),
            InlineKeyboardButton("🎲 Games", callback_data="help_games"),
        ],
        [
            InlineKeyboardButton("📊 প্রোফাইল | My Profile", callback_data="help_profile"),
            InlineKeyboardButton("📜 সব কমান্ড | All Commands", callback_data="help_main"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return welcome_text, reply_markup


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rich Welcome message with Buttons for Shariar Tech Bot."""
    user = update.effective_user
    track_user(user.id)
    track_command("start")

    welcome_text, reply_markup = _build_start_menu(user.first_name)

    await update.message.reply_text(
        text=welcome_text,
        reply_markup=reply_markup,
        parse_mode="HTML",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Passes user messages or photos to the AI with conversation memory and streaming."""
    if not API_STATE.get("groq", True):
        await update.message.reply_text(
            "🤖 Groq AI Chat is currently disabled by the Admin. Please try again later."
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
    """Handle button clicks from the inline keyboard."""
    query = update.callback_query
    await query.answer()

    HELP_MESSAGES = {
        "help_image": (
            "🎨 <b>AI Art Generation</b>\n\n"
            "To generate an image, use:\n"
            "<code>/image &lt;your prompt&gt;</code>\n\n"
            "Example: <code>/image a futuristic city</code>"
        ),
        "help_find": (
            "🛒 <b>Daraz Deal Finder</b>\n\n"
            "To find deals, use:\n"
            "<code>/find &lt;product&gt;</code>\n\n"
            "Example: <code>/find gaming mouse</code>"
        ),
        "help_weather": (
            "🌤️ <b>Live Weather Check</b>\n\n"
            "To check the weather, use:\n"
            "<code>/weather &lt;city name&gt;</code>\n\n"
            "Example: <code>/weather Tokyo</code>"
        ),
        "help_tts": (
            "🎙️ <b>Natural Text to Speech</b>\n\n"
            "Produce clear, neural voice messages:\n\n"
            "👨 <b>Boy Voice:</b> <code>/say &lt;text&gt;</code>\n"
            "👩 <b>Girl Voice:</b> <code>/say_as_girl &lt;text&gt;</code>\n\n"
            "Example: <code>/say আমার নাম লুসিফার</code>"
        ),
        "help_translate": (
            "🌐 <b>Translation</b>\n\n"
            "Auto-detect language and translate:\n"
            "<code>/translate &lt;text&gt;</code>\n\n"
            "Supports ALL languages!\n"
            "🇧🇩 Bangla → English\n"
            "🇬🇧 English → Bangla\n"
            "🇯🇵 Japanese → Bangla + English\n"
            "...and any other pair!\n\n"
            "Example: <code>/translate আমি ভালো আছি</code>"
        ),
        "help_currency": (
            "💱 <b>Currency Converter</b>\n\n"
            "Usage: <code>/convert &lt;amount&gt; &lt;FROM&gt; to &lt;TO&gt;</code>\n\n"
            "Example: <code>/convert 100 USD to BDT</code>"
        ),
        "help_qr": (
            "📱 <b>QR Code Generator</b>\n\n"
            "Usage: <code>/qr &lt;text or URL&gt;</code>\n\n"
            "Example: <code>/qr https://github.com</code>"
        ),
        "help_quiz": (
            "🧩 <b>AI Quiz Game</b>\n\n"
            "Usage: <code>/quiz &lt;topic&gt;</code>\n\n"
            "Examples:\n"
            "• <code>/quiz science</code>\n"
            "• <code>/quiz bangladesh history</code>\n"
            "• <code>/quiz programming</code>"
        ),
        "help_persona": (
            "🎭 <b>AI Persona Switcher</b>\n\n"
            "Change how I respond:\n"
            "<code>/persona</code> — Show options\n\n"
            "Available:\n"
            "🧠 Default | 👨‍🏫 Teacher\n"
            "😎 Friend | 💻 Coder\n"
            "🇧🇩 বাংলা শিক্ষক | 😈 Lucifer"
        ),
        "help_ocr": (
            "📄 <b>OCR — Text Extraction</b>\n\n"
            "Reply to a photo with <code>/ocr</code> to extract text.\n\n"
            "Supports English and Bangla!"
        ),
        "help_download": (
            "📥 <b>Media Downloader</b>\n\n"
            "Usage: <code>/download &lt;URL&gt;</code>\n\n"
            "Download videos/audio from YouTube, Instagram, TikTok, Facebook, and 1000+ other sites.\n\n"
            "Example: <code>/download https://youtube.com/watch?v=dQw4w9WgXcQ</code>"
        ),
        "help_games": (
            "🎲 <b>AI Interactive Games</b>\n\n"
            "Usage: <code>/play</code> — Choose a game!\n\n"
            "Available Games:\n"
            "• 📖 Word Chain (শব্দের খেলা)\n"
            "• 🎤 Bangla Antakshari (অন্ত্যাক্ষরী)\n"
            "• 🛍️ Haat-Bazaar Bargaining (হাট-বাজার)\n\n"
            "Stop anytime: <code>/stopgame</code>"
        ),
        "help_profile": (
            "📊 <b>User Profile & Stats</b>\n\n"
            "Usage: <code>/me</code>\n\n"
            "View your personal statistics, including:\n"
            "• Your user rank and ID\n"
            "• Chat memory and active persona\n"
            "• Quiz scores and accuracy\n"
            "• Game points and active games"
        ),
        "help_news": (
            "📰 <b>Daily News Digest</b>\n\n"
            "Usage: <code>/news</code> or <code>/news bn</code>\n\n"
            "Fetches the latest headlines from BBC World and The Daily Star!"
        ),
        "help_sticker": (
            "🖼️ <b>Sticker Maker</b>\n\n"
            "Create Telegram stickers instantly for FREE!\n\n"
            "<b>Option 1:</b> Reply to any photo with <code>/sticker</code>\n"
            "<b>Option 2:</b> Generate one with AI: <code>/sticker cute baby dragon</code>"
        ),
        "help_main": (
            "📜 <b>All Commands</b>\n\n"
            "• /start - Main menu\n"
            "• /image &lt;prompt&gt; - AI Art\n"
            "• /find &lt;product&gt; - Daraz Deals\n"
            "• /weather &lt;city&gt; - Live Weather\n"
            "• /say &lt;text&gt; - Boy Voice\n"
            "• /say_as_girl &lt;text&gt; - Girl Voice\n"
            "• /translate &lt;text&gt; - Translation\n"
            "• /convert &lt;amount&gt; &lt;FROM&gt; to &lt;TO&gt; - Currency\n"
            "• /qr &lt;text&gt; - QR Code\n"
            "• /quiz &lt;topic&gt; - Trivia Game\n"
            "• /ocr - Text from Image\n"
            "• /download &lt;url&gt; - Download Media\n"
            "• /news [bd] - Latest News\n"
            "• /persona - Switch AI Style\n"
            "• /play - Interactive Games\n"
            "• /me - Your Profile &amp; Stats\n"
            "• /clear - Clear Chat History\n"
            "• 🎤 Voice Messages - Voice Chat!"
        ),
    }

    message = HELP_MESSAGES.get(query.data, "Unknown action.")

    # Add a "Back to Menu" button on help messages
    back_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 মেনুতে ফিরুন | Back to Menu", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text=message, parse_mode="HTML", reply_markup=back_button)


async def back_to_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Back to Menu' button — rebuild the /start menu inline."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    welcome_text, reply_markup = _build_start_menu(user.first_name)

    await query.edit_message_text(
        text=welcome_text,
        reply_markup=reply_markup,
        parse_mode="HTML",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple help fallback — redirects to /start."""
    await update.message.reply_text("Use /start to see the full menu with all features!")