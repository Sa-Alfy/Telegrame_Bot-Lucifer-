import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from services.daraz_service import get_best_daraz_deal
from state import API_STATE
from utils.logger import get_logger

logger = get_logger(__name__)

async def find_deal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for the /find command.
    Searches Daraz for the best deal and sends it back to the user.
    """
    
    if not API_STATE.get("daraz", True):
        await update.message.reply_text("🛒 Daraz Deal Finder is currently disabled by the Admin. Please try again later.")
        return
        
    # Check if the user provided search terms
    if not context.args:
        await update.message.reply_text("❌ Please provide a product name. Example: `/find gaming mouse`")
        return

    query = " ".join(context.args)
    sent_message = await update.message.reply_text(f"🔍 Searching Daraz for the best deal on '{query}'...")

    # Fetch the best product data asynchronously to not block the bot
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, get_best_daraz_deal, query)

    if result.get("success"):
        product = result["data"]
        name = product.get('name')
        price = product.get('priceShow')
        
        # Round the rating score (it comes as a long float)
        rating_raw = product.get('ratingScore')
        try:
            rating = f"{float(rating_raw):.1f}" if rating_raw else "N/A"
        except (ValueError, TypeError):
            rating = "N/A"
            
        reviews = product.get('review', '0')
        url = f"https:{product.get('itemUrl')}"
        image = product.get('image')

        caption = (
            f"🏆 **Best Deal Found!**\n\n"
            f"📦 **Product:** {name}\n"
            f"💰 **Price:** {price}\n"
            f"⭐ **Rating:** {rating} ({reviews} reviews)\n\n"
            f"🔗 [View on Daraz]({url})"
        )
        
        try:
            if image:
                await update.message.reply_photo(photo=image, caption=caption, parse_mode="Markdown")
            else:
                await update.message.reply_text(caption, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error sending Daraz deal photo: {e}")
            # Fallback if image fails or doesn't exist
            await update.message.reply_text(caption, parse_mode="Markdown")
            
        await sent_message.delete()
    else:
        error_msg = result.get("error", "Unknown error occurred.")
        logger.warning(f"Daraz deal failed: {error_msg}")
        await sent_message.edit_text(f"😔 Sorry, I couldn't find any good deals for '{query}'.\n\n**Reason:** {error_msg}", parse_mode="Markdown")
