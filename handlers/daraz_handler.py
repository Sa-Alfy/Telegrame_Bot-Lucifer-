import asyncio
from telegram import Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.daraz_service import get_best_daraz_deal
from state import API_STATE
from utils.decorators import rate_limit
from utils.logger import get_logger

logger = get_logger(__name__)

# Fallback image if a product has no thumbnail
FALLBACK_IMAGE = "https://img.drz.lazcdn.com/static/bd/p/0f6c48ebc244f392375eb83c498f8a61.png"


def build_product_caption(product: dict, index: int) -> str:
    """
    Build a rich, informative caption for a single product photo.
    Telegram captions support up to 1024 chars — keep it concise.
    """
    label = product.get('_label', f'📦 Option {index + 1}')
    name = product.get('name', 'Unknown')[:70]
    price = product.get('price', 'N/A')
    original_price = product.get('original_price', '')
    discount = product.get('discount', '')
    rating = product.get('rating', 0)
    reviews = product.get('reviews', 0)
    sold_count = product.get('sold_count', '')
    location = product.get('location', '')
    is_suspicious = product.get('_suspicious', False)
    url = product.get('url', '')

    lines = []

    # Header
    lines.append(f"{label}")
    if is_suspicious:
        lines.append("🚩 SUSPICIOUS PRICE")
    lines.append(f"🔹 {name}")

    # Price block
    if discount and original_price:
        lines.append(f"💵 {price}  (was {original_price} — {discount})")
    else:
        lines.append(f"💵 {price}")

    # Rating & reviews
    if rating and rating > 0:
        stars = "⭐" * min(int(round(rating)), 5)
        lines.append(f"{stars} {rating:.1f} ({reviews} reviews)")
    else:
        lines.append("⚠️ No ratings yet")

    # Sold count
    if sold_count:
        lines.append(f"📈 {sold_count} sold")

    # Location
    if location:
        lines.append(f"📍 {location}")

    # Link
    if url:
        lines.append(f"\n🔗 View: {url}")

    return "\n".join(lines)


@rate_limit(seconds=10)
async def find_deal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for the /find command.
    Searches Daraz and sends a visually rich photo album of top products.
    """
    
    if not API_STATE.get("daraz", True):
        await update.message.reply_text("🛒 Daraz Deal Finder is currently disabled by the Admin. Please try again later.")
        return
        
    # Check if the user provided search terms
    if not context.args:
        await update.message.reply_text(
            "🛒 <b>Daraz Deal Finder</b>\n\n"
            "Usage: <code>/find &lt;product name&gt;</code>\n\n"
            "Examples:\n"
            "• <code>/find gaming mouse</code>\n"
            "• <code>/find laptop 512gb</code>\n"
            "• <code>/find wireless earbuds</code>\n\n"
            "💡 <i>Tip: Be specific for better results!</i>",
            parse_mode="HTML"
        )
        return

    query = " ".join(context.args)
    sent_message = await update.message.reply_text(
        f"🔍 Searching Daraz for <b>'{query}'</b>...\n"
        f"⏳ Finding the best deals with images...",
        parse_mode="HTML"
    )

    # Fetch product data asynchronously
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, get_best_daraz_deal, query)

    if not result.get("success"):
        error_msg = result.get("error", "Unknown error occurred.")
        logger.warning(f"Daraz deal failed: {error_msg}")
        await sent_message.edit_text(
            f"😔 Sorry, I couldn't find any deals for <b>'{query}'</b>.\n\n"
            f"<b>Reason:</b> {error_msg}\n\n"
            f"💡 <i>Tips:</i>\n"
            f"• Try simpler keywords\n"
            f"• Check your spelling\n"
            f"• Use English product names",
            parse_mode="HTML"
        )
        return

    products = result["data"]

    if not products:
        await sent_message.edit_text(f"😔 No relevant products found for '{query}'.")
        return

    # --- Build Photo Album (Telegram supports up to 10 in one album) ---
    media_group = []
    
    for i, product in enumerate(products):
        image_url = product.get('image', '') or FALLBACK_IMAGE
        caption = build_product_caption(product, i)

        # Telegram caption limit is 1024 chars
        if len(caption) > 1024:
            caption = caption[:1020] + "..."

        media_group.append(
            InputMediaPhoto(
                media=image_url,
                caption=caption,
                parse_mode=None,  # Plain text for album captions (Markdown has issues in albums)
            )
        )

    # --- Send the album ---
    try:
        # Update status
        await sent_message.edit_text(
            f"🧺 Found <b>{len(products)} deals</b> for <b>'{query}'</b>!\n"
            f"📸 Sending product cards...",
            parse_mode="HTML"
        )

        # Send media group (photo album)
        await update.message.reply_media_group(media=media_group)

        # Send a summary footer with general info
        summary_lines = [
            f"━━━━━━━━━━━━━━━━━━━━",
            f"🧺 <b>{len(products)} deals found for '{query}'</b>",
            f"━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        # Quick legend
        labels_found = [p.get('_label', '') for p in products]
        if any('Budget' in l for l in labels_found):
            summary_lines.append("💰 <b>Budget Pick</b> — Cheapest relevant option")
        if any('Best Match' in l for l in labels_found):
            summary_lines.append("🏆 <b>Best Match</b> — Highest overall score")
        if any('Top Quality' in l for l in labels_found):
            summary_lines.append("⭐ <b>Top Quality</b> — Best rated product")
        if any('Best Seller' in l for l in labels_found):
            summary_lines.append("🔥 <b>Best Seller</b> — Most sold product")
        if any('SUSPICIOUS' in str(p.get('_suspicious', '')) for p in products if p.get('_suspicious')):
            summary_lines.append("🚩 <b>Suspicious</b> — Price may be too good to be true")

        summary_lines.append("")
        summary_lines.append("💡 <i>Prices and availability change fast! Swipe ← → to compare deals.</i>")
        
        summary_text = "\n".join(summary_lines)

        # Create Buy Now inline buttons for each product
        keyboard = []
        row = []
        for i, product in enumerate(products):
            product_url = product.get('url', '')
            if not product_url:
                continue
                
            label = product.get('_label', '')
            short_label = label.split(" — ")[0].strip() if " — " in label else ""
            if not short_label:
                short_label = f"🛍️ Item {i + 1}"
                
            # e.g., "1. 💰 Budget Pick" or "2. 🛍️ Item 2"
            button_text = f"{i + 1}. {short_label}"
            
            button = InlineKeyboardButton(button_text, url=product_url)
            row.append(button)
            
            if len(row) == 2:
                keyboard.append(row)
                row = []
                
        if row:
            keyboard.append(row)
            
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        await update.message.reply_text(
            summary_text, 
            parse_mode="HTML",
            reply_markup=reply_markup
        )

        # Clean up the loading message
        try:
            await sent_message.delete()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Error sending Daraz album: {e}")
        
        # Fallback: If album fails (e.g. image URLs broken), send as text
        await _send_text_fallback(update, sent_message, products, query)


async def _send_text_fallback(update, sent_message, products, query):
    """
    Fallback text-only display if photo album fails.
    """
    try:
        summary_text = f"🧺 <b>Top Deals for '{query}'</b>\n"
        summary_text += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, product in enumerate(products):
            label = product.get('_label', f'📦 Option {i+1}')
            name = product.get('name', 'Unknown')[:60]
            price = product.get('price', 'N/A')
            original_price = product.get('original_price', '')
            discount = product.get('discount', '')
            rating = product.get('rating', 0)
            reviews = product.get('reviews', 0)
            sold_count = product.get('sold_count', '')
            url = product.get('url', '')
            is_suspicious = product.get('_suspicious', False)
            
            status = " 🚩 <b>SUSPICIOUS</b>" if is_suspicious else ""
            relevance = product.get('_relevance', 0)
            if relevance > 80:
                status += " ✅"
            
            summary_text += f"{label}{status}\n"
            summary_text += f"🔹 <b>{name}...</b>\n"
            
            if discount and original_price:
                summary_text += f"💵 <b>{price}</b> <s>{original_price}</s> ({discount})\n"
            else:
                summary_text += f"💵 <b>{price}</b>\n"
            
            if rating and rating > 0:
                summary_text += f"⭐ <b>{rating:.1f}</b> ({reviews} reviews)\n"
            else:
                summary_text += f"⚠️ <i>No ratings</i>\n"
                
            if sold_count:
                summary_text += f"📈 {sold_count} sold\n"
                
            if url:
                summary_text += f'🔗 <a href="{url}">View Product</a>\n'
            
            summary_text += "\n"

        summary_text += "━━━━━━━━━━━━━━━━━━━━\n"
        summary_text += "💡 <i>Prices and availability change fast!</i>"

        await update.message.reply_text(summary_text, parse_mode="HTML", disable_web_page_preview=True)
        
        try:
            await sent_message.delete()
        except Exception:
            pass
            
    except Exception as e:
        logger.error(f"Text fallback also failed: {e}")
        await sent_message.edit_text("😔 Error displaying results. Please try a simpler search query.")
