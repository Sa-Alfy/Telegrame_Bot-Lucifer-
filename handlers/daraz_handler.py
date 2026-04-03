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
    Searches Daraz for multiple deals and returns a tiered summary.
    """
    
    if not API_STATE.get("daraz", True):
        await update.message.reply_text("🛒 Daraz Deal Finder is currently disabled by the Admin. Please try again later.")
        return
        
    # Check if the user provided search terms
    if not context.args:
        await update.message.reply_text("❌ Please provide a product name. Example: `/find gaming mouse`")
        return

    query = " ".join(context.args)
    sent_message = await update.message.reply_text(f"🔍 Searching Daraz for the best '{query}' deals...")

    # Fetch product data asynchronously
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, get_best_daraz_deal, query)

    if result.get("success"):
        products = result["data"] # This is now a list of up to 6 items
        
        summary_text = f"🧺 **Top Deals for '{query}'**\n"
        summary_text += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, product in enumerate(products):
            name = product.get('name', 'Unknown')
            price = product.get('priceShow', 'N/A')
            url = f"https:{product.get('itemUrl')}"
            
            # Smart Indicators
            relevance = product.get('_relevance', 0)
            is_suspicious = product.get('_suspicious', False)
            
            # Rating logic
            rating_raw = product.get('ratingScore')
            reviews = product.get('review', '0')
            
            try:
                rating = f"{float(rating_raw):.1f}" if (rating_raw and float(rating_raw) > 0) else None
            except:
                rating = None
                
            # Pick a label based on the sort order
            label = ""
            if i == 0: label = "💰 **Budget Pick**"
            elif i == 1: label = "🏆 **Best Match**"
            elif i == 2: label = "⭐ **Top Quality**"
            else: label = f"📦 **Option {i+1}**"
            
            # Add Status Icons
            status_icons = ""
            if relevance > 80: status_icons += " ✅" # High accuracy
            if is_suspicious: status_icons += " 🚩 *[SUSPICIOUS PRICE]*"
            
            summary_text += f"{label}{status_icons}\n"
            summary_text += f"🔹 **{name[:60]}...**\n"
            summary_text += f"💵 **Price:** {price}\n"
            
            if rating:
                summary_text += f"⭐ **Rating:** {rating} ({reviews} reviews)\n"
            else:
                summary_text += f"⚠️ *No ratings - proceed with caution*\n"
                
            summary_text += f"🔗 [View Product]({url})\n\n"

        summary_text += "━━━━━━━━━━━━━━━━━━━━\n"
        summary_text += "💡 *Tip: Prices and availability change fast!*"

        # Send the summary as a text message
        try:
            await update.message.reply_text(summary_text, parse_mode="Markdown", disable_web_page_preview=True)
            await sent_message.delete()
        except Exception as e:
            logger.error(f"Error sending Daraz summary: {e}")
            await sent_message.edit_text("😔 Error displaying results. Please try a simpler search query.")

    else:
        error_msg = result.get("error", "Unknown error occurred.")
        logger.warning(f"Daraz deal failed: {error_msg}")
        await sent_message.edit_text(f"😔 Sorry, I couldn't find any good deals for '{query}'.\n\n**Reason:** {error_msg}", parse_mode="Markdown")
