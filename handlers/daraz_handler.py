import asyncio
import uuid
import math
from telegram import Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.daraz_service import get_best_daraz_deal
from state import API_STATE
from utils.decorators import rate_limit
from utils.logger import get_logger
from handlers.basic import get_home_button
from utils.ux import ux_card
from utils.cache import daraz_cache, DARAZ_TTL

logger = get_logger(__name__)

FALLBACK_IMAGE = "https://img.drz.lazcdn.com/static/bd/p/0f6c48ebc244f392375eb83c498f8a61.png"

def generate_pros_cons(rating: float) -> str:
    """Generate simulated pros and cons based on the rating."""
    if rating >= 4.7:
        return "👍 **Pros:**\n• Exceptional quality\n• Highly praised by buyers\n\n👎 **Cons:**\n• Often sells out quickly"
    elif rating >= 4.0:
        return "👍 **Pros:**\n• Great value for money\n• Reliable performance\n\n👎 **Cons:**\n• Packaging can be basic"
    elif rating >= 3.0:
        return "👍 **Pros:**\n• Average tier option\n\n👎 **Cons:**\n• Mixed reviews\n• Build quality varies"
    elif rating > 0:
        text = "👍 **Pros:**\n• Budget-level pricing\n\n👎 **Cons:**\n• Low overall ratings\n• Higher risk of issues"
    else:
        text = "⚠️ _No detailed reviews available yet._"
    
    return f"{text}\n\n<i>(Simulated by AI based on rating)</i>"

@rate_limit(seconds=10)
async def find_deal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for the /find command.
    Searches Daraz and sends the Best Pick (Screen 1).
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

    # Keep a good number of results so pagination makes sense (30 items = 10 pages)
    products = result.get("data", [])[:30]
    if not products:
        await sent_message.edit_text(f"😔 No relevant products found for '{query}'.")
        return

    session_id = str(uuid.uuid4())[:8]
    # State includes both the list and the query to maintain context
    session_data = {"query": query, "results": products}
    daraz_cache.set(session_id, session_data, DARAZ_TTL)

    await sent_message.edit_text(f"✅ <b>Lucifer:</b> Finalizing results for '{query}'...", parse_mode="HTML")
    await render_main_screen(sent_message, session_id, session_data)

# ----------------- SCREEN RENDERERS ----------------- #

async def render_main_screen(message, session_id: str, session_data: dict, edit_media=False):
    """SCREEN 1 - Smart Result (Best Pick)"""
    p = session_data["results"][0]
    # Wrap in UX card
    caption_html = ux_card(
        f"📱 <b>{p.get('_label', 'Budget Pick')}</b>\n\n"
        f"<b>{p.get('name', 'Unknown product')[:80]}...</b>\n"
        f"💰 {p.get('price', 'N/A')}   ⭐ {p.get('rating', 0)}\n\n"
        f"💡 <i>Highest scored option based on relevance and price.</i>",
        title="🛒 Smart Selection"
    )
    
    image_url = p.get('image', '') or FALLBACK_IMAGE

    keyboard = [
        [InlineKeyboardButton("🛒 View Details", callback_data=f"daraz:view:{session_id}:0")],
        [
            InlineKeyboardButton("📊 Compare", callback_data=f"daraz:compare:{session_id}:0"),
            InlineKeyboardButton("🔄 More Options", callback_data=f"daraz:list:{session_id}:0")
        ],
    ]
    # Standardized interaction row (Phase 3)
    standard_kb = get_home_button().inline_keyboard
    keyboard.extend(standard_kb)

    media = InputMediaPhoto(media=image_url, caption=caption_html, parse_mode="HTML")
    
    try:
        if edit_media:
            await message.edit_media(media=media, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await message.reply_photo(photo=image_url, caption=caption_html, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            try:
                await message.delete()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error rendering main screen: {e}")
        try:
            await message.edit_caption(caption=caption_html, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except Exception:
            pass


async def render_list_screen(message, session_id: str, session_data: dict, page: int):
    """SCREEN 2 - Top Choices (Paginated)"""
    products = session_data["results"]
    items_per_page = 3
    total_pages = math.ceil(len(products) / items_per_page)
    
    if page >= total_pages or page < 0:
        page = 0
        
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    current_items = products[start_idx:end_idx]

    caption_lines = [f"📋 **Top Choices (Page {page+1}/{total_pages})**\n"]
    
    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
    
    keyboard_selectors = []
    
    for i, p in enumerate(current_items):
        global_idx = start_idx + i
        emoji = number_emojis[i] if i < len(number_emojis) else f"{i+1}."
        
        name = p.get('name', 'Unknown')[:40] + "..."
        price = p.get('price', 'N/A')
        rating = p.get('rating', 0)
        
        caption_lines.append(f"{emoji} **{name}**")
        caption_lines.append(f"💰 {price}  ⭐ {rating}\n")
        
        keyboard_selectors.append(InlineKeyboardButton(emoji, callback_data=f"daraz:view:{session_id}:{global_idx}"))

    # Update the media to the first item on the current list so it changes dynamically
    img_item = current_items[0]
    image_url = img_item.get('image', '') or FALLBACK_IMAGE
    img_name = img_item.get('name', 'Product')[:30] + "..."
    
    caption_lines.insert(0, f"🖼️ _Currently displaying image for: {number_emojis[0]} {img_name}_\n━━━━━━━━━━━━━━━━━━")

    caption_lines.append("👇 **Select an option below to view its details & photo:**")
    caption = "\n".join(caption_lines)

    kb = [keyboard_selectors]
    
    if page == 0 and len(products) > 1:
        kb.append([InlineKeyboardButton("📊 Compare Best 2", callback_data=f"daraz:compare:{session_id}:0")])
        
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"daraz:list:{session_id}:{page-1}"))
    if total_pages > 1 and page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("🔄 Next Page", callback_data=f"daraz:list:{session_id}:{page+1}"))
        
    if nav_row:
        kb.append(nav_row)
        
    kb.append([InlineKeyboardButton("🔙 Back to Main Screen", callback_data=f"daraz:main:{session_id}:0")])

    media = InputMediaPhoto(media=image_url, caption=caption, parse_mode="Markdown")

    try:
        await message.edit_media(media=media, reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        logger.error(f"Error rendering list screen media: {e}")
        try:
            await message.edit_caption(caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except: pass


async def render_detail_screen(message, session_id: str, session_data: dict, index: int):
    """SCREEN 3 - Product Detail"""
    products = session_data["results"]
    if index >= len(products) or index < 0:
        index = 0
        
    p = products[index]
    page = index // 3
    
    name = p.get('name', 'Unknown')
    price = p.get('price', 'N/A')
    rating = p.get('rating', 0)
    sold = p.get('sold_count', '')
    url = p.get('url', 'https://daraz.com.bd')
    image_url = p.get('image', '') or FALLBACK_IMAGE

    caption = (
        f"📱 **{name[:80]}...**\n\n"
        f"💰 **{price}**\n"
        f"⭐ {rating} / 5.0"
    )
    if sold: caption += f"   📦 {sold} sold"
    
    caption += f"\n\n{generate_pros_cons(rating)}"
    
    kb = [
        [InlineKeyboardButton("🛒 Open in Daraz", url=url)],
        [InlineKeyboardButton("📊 Compare", callback_data=f"daraz:compare:{session_id}:{index}")],
        [InlineKeyboardButton("🔙 Back to List", callback_data=f"daraz:list:{session_id}:{page}")]
    ]
    # Standardized interaction row (Phase 3)
    kb.extend(get_home_button().inline_keyboard)
    
    media = InputMediaPhoto(media=image_url, caption=caption, parse_mode="Markdown")
    try:
        await message.edit_media(media=media, reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        logger.error(f"Error editing media in detail screen: {e}")
        try:
            await message.edit_caption(caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except Exception:
            pass


async def render_compare_screen(message, session_id: str, session_data: dict, index: int):
    """SCREEN 4 - Compare 2 Items"""
    products = session_data["results"]
    idx1 = index
    idx2 = index + 1 if index + 1 < len(products) else 0
    
    if idx1 == idx2:
        return
        
    p1 = products[idx1]
    p2 = products[idx2]
    page = index // 3
    
    n1 = p1.get('name', 'Item 1')[:30] + "..."
    n2 = p2.get('name', 'Item 2')[:30] + "..."
    
    comp = (
        f"⚖️ **Quick Comparison**\n\n"
        f"**1️⃣ {n1}**\n"
        f"💰 {p1.get('price')}  |  ⭐ {p1.get('rating', 0)}\n\n"
        f"**VS**\n\n"
        f"**2️⃣ {n2}**\n"
        f"💰 {p2.get('price')}  |  ⭐ {p2.get('rating', 0)}\n\n"
    )
    
    v1 = p1.get('_price_val', 0)
    v2 = p2.get('_price_val', 0)
    r1 = p1.get('rating', 0)
    r2 = p2.get('rating', 0)
    
    if r1 > r2 and v1 <= v2:
        comp += "🏆 **Winner:** Option 1 (Better rating & price)"
    elif r2 > r1 and v2 <= v1:
        comp += "🏆 **Winner:** Option 2 (Better rating & price)"
    elif v1 < v2:
        comp += "💰 **Budget Pick:** Option 1 is cheaper"
    elif v2 < v1:
        comp += "💰 **Budget Pick:** Option 2 is cheaper"
    else:
        comp += "🤝 **Tie:** Both offer similar value."

    kb = [
        [
            InlineKeyboardButton("◀️ View 1", callback_data=f"daraz:view:{session_id}:{idx1}"),
            InlineKeyboardButton("View 2 ▶️", callback_data=f"daraz:view:{session_id}:{idx2}")
        ],
        [InlineKeyboardButton("🔙 Back to List", callback_data=f"daraz:list:{session_id}:{page}")]
    ]
    
    # Render with the image of item 1 for visual anchor
    img_url = p1.get('image', '') or p2.get('image', '') or FALLBACK_IMAGE
    media = InputMediaPhoto(media=img_url, caption=comp, parse_mode="Markdown")

    try:
        await message.edit_media(media=media, reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        try:
            await message.edit_caption(caption=comp, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except Exception:
            pass


# ----------------- ROUTER ----------------- #

async def daraz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles all state transitions for Daraz flows.
    Format: daraz:<action>:<session_id>:<index_or_page>
    """
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    if len(parts) < 4: return
        
    action, session_id = parts[1], parts[2]
    try:
        target_val = int(parts[3])
    except ValueError: 
        target_val = 0

    if action == "cancel":
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    # Check cache based session
    data = daraz_cache.get(session_id)
    session_data = None
    
    if data:
        # Gracefully handle if the previous implementation's data shape was just a list
        if isinstance(data, list):
            session_data = {"query": "Unknown", "results": data}
        else:
            session_data = data

    if not session_data or "results" not in session_data:
        try:
            await query.edit_message_caption(caption="⏳ Session expired. Please search again using /find.")
        except Exception:
            pass
        return

    # Route to appropriate screen based on state machine
    try:
        if action == "main":
            await render_main_screen(query.message, session_id, session_data, edit_media=True)
        elif action == "list":
            await render_list_screen(query.message, session_id, session_data, target_val)
        elif action == "view":
            await render_detail_screen(query.message, session_id, session_data, target_val)
        elif action == "compare":
            await render_compare_screen(query.message, session_id, session_data, target_val)
    except Exception as e:
        logger.error(f"Error in daraz router: {e}")
