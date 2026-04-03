from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import base64
from services.ai_chat import get_ai_response
from state import API_STATE

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rich Welcome message with Buttons for Shariar Tech Bot."""
    user = update.effective_user
    
    # Professional Greeting
    welcome_text = (
        f"👋 *Hi {user.first_name}! I am the Shariar Tech Bot.*\n\n"
        "I'm a modular assistant designed to help you with AI tasks and shopping.\n\n"
        "🚀 *My Current Functions:*\n"
        "🤖 **AI Chat:** Just talk to me normally!\n"
        "🎨 **AI Art:** Use `/image` to create visuals.\n"
        "🛒 **Daraz Finder:** Use `/find` to track prices.\n"
        "🌤️ **Weather:** Use `/weather` to check any city.\n\n"
        "👇 *Quick Actions:* "
    )

    # Creating the Button Grid
    keyboard = [
        [
            InlineKeyboardButton("🎨 Create AI Art", callback_data='help_image'),
            InlineKeyboardButton("🛒 Find Best Deal", callback_data='help_find')
        ],
        [
            InlineKeyboardButton("🌤️ Check Weather", callback_data='help_weather'),
            InlineKeyboardButton("📜 View All Commands", callback_data='help_main')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text=welcome_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Passes user messages or photos to the AI and returns the response"""
    if not API_STATE.get("groq", True):
        await update.message.reply_text("🤖 Groq AI Chat is currently disabled by the Admin. Please try again later.")
        return
        
    image_bytes = None
    if update.message.photo:
        # Get the highest resolution photo sent
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        image_bytes = await photo_file.download_as_bytearray()
        
    # Get the text prompt (from message text or image caption)
    user_text = update.message.caption if update.message.photo else update.message.text
    
    # If they sent an image with no caption at all, inject a default prompt
    if not user_text and image_bytes:
        user_text = "Please analyze this image."
        
    # Let the user know the bot is thinking
    sent_message = await update.message.reply_text("🤔 Thinking...")
    
    # Get response from AI (passing the image if it exists)
    response = await get_ai_response(user_text, image_bytes=image_bytes)
    
    # Edit the "Thinking..." message to be the AI's final answer (plain text — no Markdown conflicts)
    await sent_message.edit_text(response)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks from the inline keyboard."""
    query = update.callback_query
    await query.answer() # Acknowledge the click
    
    if query.data == 'help_image':
        message = "🎨 **AI Art Generation**\n\nTo generate an image, use:\n`/image <your prompt>`\n\nExample: `/image a futuristic city`"
    elif query.data == 'help_find':
        message = "🛒 **Daraz Deal Finder**\n\nTo find deals, use:\n`/find <product>`\n\nExample: `/find gaming mouse`"
    elif query.data == 'help_weather':
        message = "🌤️ **Live Weather Check**\n\nTo check the weather, use:\n`/weather <city name>`\n\nExample: `/weather Tokyo`"
    elif query.data == 'help_main':
        message = "📜 **All Commands**\n\n• /start - Main menu\n• /image <prompt> - AI Art\n• /find <product> - Daraz Deals\n• /weather <city> - Live Weather"
    else:
        message = "Unknown action."
        
    await query.edit_message_text(text=message, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple help fallback."""
    await update.message.reply_text("Use /start to see the main menu!")