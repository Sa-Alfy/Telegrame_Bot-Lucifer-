import asyncio
from telegram import Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.daraz_service import get_best_daraz_deal
from state import API_STATE
from utils.decorators import rate_limit
from utils.logger import get_logger

logger = get_logger(__name__)

FALLBACK_IMAGE = "https://img.drz.lazcdn.com/static/bd/p/0f6c48ebc244f392375eb83c498f8a61.png"

@rate_limit(seconds=10)
async def find_deal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for the /find command.
    Searches Daraz and sends a Media Group (Album) of the Top 3 items.
    """
    if not API_STATE.get("daraz", True):
        await update.message.reply_text("🛒 Daraz Assistant is currently disabled by Admin.")
        return
        
    if not context.args:
        await update.message.reply_text(
            "🛒 <b>Daraz Shopping Assistant</b>\n\n"
            "Usage: <code>/find &lt;product name&gt;</code>\n\n"
            "Example: <code>/find smart watch</code>\n"
            "💡 <i>Tip: Be specific for better results!</i>",
            parse_mode="HTML"
        )
        return

    query = " ".join(context.args)
    sent_message = await update.message.reply_text(
        f"🔍 <b>Lucifer:</b> Searching Daraz for '{query}'...",
        parse_mode="HTML"
    )
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, get_best_daraz_deal, query)

    await sent_message.edit_text(f"📊 <b>Lucifer:</b> Analyzing best options for '{query}'...", parse_mode="HTML")

    if not result.get("success"):
        await sent_message.edit_text(f"😔 Error: {result.get('error', 'Unknown error.')}")
        return

    # Extract Top 3 items
    products = result.get("data", [])[:3]
    if not products:
        await sent_message.edit_text(f"😔 No relevant products found for '{query}'.")
        return

    await sent_message.edit_text(f"✅ <b>Lucifer:</b> Finalizing {len(products)} deals for '{query}'...", parse_mode="HTML")

    # Build the Media Group
    media_group = []
    for i, p in enumerate(products):
        name = p.get('name', 'Unknown product')[:60]
        if len(p.get('name', '')) > 60:
            name += "..."
            
        price = p.get('price', 'N/A')
        rating = p.get('rating', '0')
        url = p.get('productUrl', '#')
        image_url = p.get('image', '') or FALLBACK_IMAGE

        caption_html = (
            f"📦 <b>{name}</b>\n"
            f"💰 {price}   |   ⭐ {rating}\n"
            f"🔗 <a href='{url}'>Open in Daraz</a>"
        )

        media_group.append(InputMediaPhoto(media=image_url, caption=caption_html, parse_mode="HTML"))

    try:
        # Send the album
        await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media_group)
        
        # Delete the "Finalizing" status message to keep chat clean
        await sent_message.delete()
        
        # Send the Action Bar follow-up
        action_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Search Another Item", callback_data="result_action_deals_retry")],
            [InlineKeyboardButton("🏠 Home", callback_data="back_to_start")]
        ])
        await update.message.reply_text(
            f"Here are the top {len(products)} verified deals.",
            reply_markup=action_kb
        )
    except Exception as e:
        logger.error(f"Error sending Daraz media group: {e}")
        await sent_message.edit_text("❌ Failed to display the products. Please try again later.")
