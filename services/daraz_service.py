import cloudscraper
import json
import re
from utils.logger import get_logger

logger = get_logger(__name__)


def calculate_relevance_score(item_name: str, query_tokens: list, query_specs: list):
    """
    Calculates a relevance score (0-100+) based on keyword density and spec matching.
    """
    name_lower = item_name.lower()
    score = 0
    
    # 1. Match Descriptive Tokens (Brands, Colors, etc.) - weight 1x
    matched_words = 0
    for token in query_tokens:
        if token in name_lower:
            matched_words += 1
            score += 10
            
    # Bonus for all words matching
    if matched_words == len(query_tokens) and query_tokens:
        score += 20

    # 2. Match Spec Tokens (Numbers, units like GB, RAM) - weight 3x
    item_specs = re.findall(r'\d+', name_lower)
    
    for spec in query_specs:
        if spec in name_lower:
            score += 30  # High reward for matching specs
        else:
            if any(s != spec and s in item_specs for s in re.findall(r'\d+', ' '.join(query_specs))):
                score -= 100  # Massive penalty for wrong numbers

    return score


def extract_product_data(item: dict) -> dict:
    """
    Extracts and normalizes all useful fields from a Daraz API product item.
    Returns a clean dict with all the data we need for rich display.
    """
    # --- Image ---
    image_url = item.get('image', '')
    if image_url and not image_url.startswith('http'):
        image_url = f"https:{image_url}"

    # --- Prices ---
    price_show = item.get('priceShow', 'N/A')
    
    original_price = item.get('originalPrice', '')
    original_price_show = item.get('originalPriceShow', '')
    
    # Calculate discount
    discount = item.get('discount', '')
    if not discount:
        try:
            current = float(str(price_show).replace('৳', '').replace(',', '').strip())
            original = float(str(original_price_show or original_price).replace('৳', '').replace(',', '').strip())
            if original > current > 0:
                discount = f"-{int(((original - current) / original) * 100)}%"
        except (ValueError, ZeroDivisionError):
            pass

    # --- Rating & Reviews ---
    try:
        rating = float(item.get('ratingScore', 0) or 0)
    except (ValueError, TypeError):
        rating = 0.0
    
    try:
        reviews = int(item.get('review', 0) or 0)
    except (ValueError, TypeError):
        reviews = 0

    # --- Sold count ---
    sold_count = item.get('itemSoldCntShow', '') or item.get('soldCount', '')

    # --- Seller & Location ---
    location = item.get('location', '')
    seller_name = item.get('sellerName', '')

    # --- URL ---
    item_url = item.get('itemUrl', '')
    if item_url and not item_url.startswith('http'):
        item_url = f"https:{item_url}"

    return {
        'name': item.get('name', 'Unknown Product'),
        'image': image_url,
        'price': price_show,
        'original_price': original_price_show or original_price,
        'discount': discount,
        'rating': rating,
        'reviews': reviews,
        'sold_count': sold_count,
        'location': location,
        'seller': seller_name,
        'url': item_url,
        # Internal scoring fields (carried from raw)
        '_raw': item,
    }


def filter_and_sort_products(items: list, query: str, max_results: int = 8):
    """
    Advanced ranking engine using weighted relevance, seller quality, and price variance.
    Returns up to max_results products sorted for optimal display.
    """
    if not items:
        return []

    # Prepare Query Tokens
    query_lower = query.lower()
    query_tokens = [w for w in query_lower.split() if not any(char.isdigit() for char in w)]
    query_specs = [w for w in query_lower.split() if any(char.isdigit() for char in w)]

    scored_items = []
    total_price = 0
    valid_prices = 0

    for item in items:
        product = extract_product_data(item)
        name = product['name']

        # --- Relevance Score ---
        relevance = calculate_relevance_score(name, query_tokens, query_specs)

        # --- Price Value ---
        price_str = str(product['price']).replace('৳', '').replace(',', '').strip()
        try:
            price_val = float(price_str)
        except (ValueError, TypeError):
            price_val = 0

        if price_val > 0:
            total_price += price_val
            valid_prices += 1

        # --- Seller/Quality Reputation Score ---
        rating = product['rating']
        reviews = product['reviews']

        # Review quality: high rating + meaningful review count
        # A product with 4.5 stars and 100 reviews > 5.0 stars with 1 review
        review_credibility = min(reviews / 20, 5)  # Cap at 5 points
        quality_score = (rating * 10) + (review_credibility * 10)

        # --- Sales Volume Signal ---
        sold_text = str(product.get('sold_count', ''))
        sold_bonus = 0
        try:
            if 'k' in sold_text.lower():
                sold_bonus = float(sold_text.lower().replace('k', '').replace('+', '').strip()) * 5
            elif sold_text.strip():
                sold_bonus = min(float(sold_text.replace('+', '').strip()) / 10, 20)
        except (ValueError, TypeError):
            pass

        # --- Final Composite Score ---
        # 50% Relevance, 25% Quality/Reviews, 15% Sales, 10% Has Image
        has_image = 1 if product['image'] else 0
        rank_score = (
            (relevance * 0.50) +
            (quality_score * 0.25) +
            (sold_bonus * 0.15) +
            (has_image * 10 * 0.10)
        )

        product['_relevance'] = relevance
        product['_quality'] = quality_score
        product['_price_val'] = price_val
        product['_rank_score'] = rank_score
        scored_items.append(product)

    # --- Scam Detection ---
    avg_price = total_price / valid_prices if valid_prices > 0 else 0
    threshold = avg_price * 0.3  # 70% cheaper = suspicious

    for item in scored_items:
        item['_suspicious'] = (
            item['_price_val'] > 0 and 
            item['_price_val'] < threshold and 
            avg_price > 500
        )

    # --- Final Selection: Diverse picks ---
    scored_items.sort(key=lambda x: x['_rank_score'], reverse=True)

    # Take top candidates pool
    candidates = scored_items[:20]

    # Filter out zero-relevance items (completely unrelated)
    candidates = [c for c in candidates if c['_relevance'] > 0] or scored_items[:max_results]

    final_picks = []

    if candidates:
        # 1. Budget Pick (cheapest among relevant)
        price_sorted = sorted([c for c in candidates if c['_price_val'] > 0], key=lambda x: x['_price_val'])
        if price_sorted:
            budget = price_sorted[0]
            budget['_label'] = '💰 Budget Pick'
            final_picks.append(budget)

        # 2. Best Match (highest rank score)
        best_match = sorted(candidates, key=lambda x: x['_rank_score'], reverse=True)[0]
        if best_match not in final_picks:
            best_match['_label'] = '🏆 Best Match'
            final_picks.append(best_match)

        # 3. Top Quality (best rating + reviews combo)
        best_quality = sorted(candidates, key=lambda x: x['_quality'], reverse=True)[0]
        if best_quality not in final_picks:
            best_quality['_label'] = '⭐ Top Quality'
            final_picks.append(best_quality)

        # 4. Best Seller (highest sold count)
        def get_sold_num(item):
            s = str(item.get('sold_count', '0'))
            try:
                if 'k' in s.lower():
                    return float(s.lower().replace('k', '').replace('+', '').strip()) * 1000
                return float(s.replace('+', '').strip()) if s.strip() else 0
            except:
                return 0

        best_seller = sorted(candidates, key=get_sold_num, reverse=True)[0]
        if best_seller not in final_picks and get_sold_num(best_seller) > 0:
            best_seller['_label'] = '🔥 Best Seller'
            final_picks.append(best_seller)

        # 5+. Fill remaining slots from top-ranked
        for item in sorted(candidates, key=lambda x: x['_rank_score'], reverse=True):
            if item not in final_picks:
                idx = len(final_picks) + 1
                item['_label'] = f'📦 Option {idx}'
                final_picks.append(item)
            if len(final_picks) >= max_results:
                break

    return final_picks


def get_best_daraz_deal(query: str):
    """
    Fetches products from Daraz and ranks them using a Generalized Scoring Engine.
    Returns enriched product data including image URLs for rich display.
    """
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "desktop": True}
    )

    api_url = f"https://www.daraz.com.bd/catalog/?ajax=true&q={query.replace(' ', '+')}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.daraz.com.bd/",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json"
    }

    try:
        response = scraper.get(api_url, headers=headers)
        
        if response.status_code == 200 and response.text.strip().startswith('{'):
            try:
                data = response.json()
            except Exception:
                return {"success": False, "error": "Invalid JSON from Daraz."}
                
            items = data.get('mods', {}).get('listItems', [])
            if items:
                processed_items = filter_and_sort_products(items, query.lower())
                # Strip internal _raw field before returning (saves memory)
                for item in processed_items:
                    item.pop('_raw', None)
                return {"success": True, "data": processed_items}
            else:
                return {"success": False, "error": "No products found for this query."}
        else:
            if response.status_code in [403, 401] or "captcha" in response.text.lower() or "slide" in response.text.lower() or "verify" in response.text.lower():
                return {"success": False, "error": "Blocked by Daraz Anti-Bot filter (Captcha/403)."}
            return {"success": False, "error": f"Bad response from Daraz: HTTP {response.status_code}"}
                
    except Exception as e:
        return {"success": False, "error": f"Network exception: {str(e)}"}