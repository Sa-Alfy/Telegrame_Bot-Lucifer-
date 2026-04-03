import cloudscraper
import json
import re

import cloudscraper
import json
import re

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
    # We want to ensure "512" doesn't match "128"
    item_specs = re.findall(r'\d+', name_lower)
    
    for spec in query_specs:
        if spec in name_lower:
            score += 30 # High reward for matching specs
        else:
            # Conflict Penalty: If query has a spec that ISN'T in this name, 
            # but the name HAS a different number, it's probably wrong.
            if any(s != spec and s in item_specs for s in re.findall(r'\d+', ' '.join(query_specs))):
                score -= 100 # Massive penalty for wrong numbers

    return score

def filter_and_sort_products(items: list, query: str):
    """
    Advanced ranking engine using weighted relevance and price variance.
    """
    if not items: return []

    # Prepare Query Tokens
    # Descriptive: words without numbers
    query_tokens = [w for w in query.split() if not any(char.isdigit() for char in w)]
    # Specs: words with numbers (512gb, 16v, etc.)
    query_specs = [w for w in query.split() if any(char.isdigit() for char in w)]

    # 1. Rank every item
    scored_items = []
    total_price = 0
    valid_prices = 0
    
    for item in items:
        name = item.get('name', '')
        relevance = calculate_relevance_score(name, query_tokens, query_specs)
        
        # Extract Price for averaging
        price_str = item.get('priceShow', '0').replace('৳', '').replace(',', '').strip()
        try:
            price_val = float(price_str)
            item['_price_val'] = price_val
            if price_val > 0:
                total_price += price_val
                valid_prices += 1
        except:
            item['_price_val'] = 0
            
        item['_relevance'] = relevance
        
        # Calculate rating weight
        rating = float(item.get('ratingScore', 0) or 0)
        reviews = int(item.get('review', 0) or 0)
        item['_quality'] = (rating * 10) + (reviews / 5)
        
        # Final Sort Score: 70% Relevance, 30% Quality
        item['_rank_score'] = (relevance * 0.7) + (item['_quality'] * 0.3)
        scored_items.append(item)

    # 2. Scam Detection (70% Price Variance)
    avg_price = total_price / valid_prices if valid_prices > 0 else 0
    threshold = avg_price * 0.3 # 70% cheaper means < 30% of average
    
    for item in scored_items:
        item['_suspicious'] = (item['_price_val'] > 0 and item['_price_val'] < threshold and avg_price > 500)

    # 3. Final Selection
    # Sort by Rank Score descending
    scored_items.sort(key=lambda x: x['_rank_score'], reverse=True)
    
    # Pick top 6, ensuring we cover different price points if possible
    results = scored_items[:10] # Take top 10 relevant
    results.sort(key=lambda x: x['_price_val']) # Sort by price
    
    final_picks = []
    if results:
        # Budget Pick
        final_picks.append(results[0])
        # Best Relevance Pick
        best_rel = sorted(results, key=lambda x: x['_rank_score'], reverse=True)[0]
        if best_rel not in final_picks:
            final_picks.append(best_rel)
            
        # Top Quality Pick
        best_qual = sorted(results, key=lambda x: x['_quality'], reverse=True)[0]
        if best_qual not in final_picks:
            final_picks.append(best_qual)
            
        # Fill remaining
        for item in sorted(results, key=lambda x: x['_rank_score'], reverse=True):
            if item not in final_picks:
                final_picks.append(item)
            if len(final_picks) >= 6:
                break
                
    return final_picks

def get_best_daraz_deal(query: str):
    """
    Fetches products from Daraz and ranks them using a Generalized Scoring Engine.
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
                return {"success": True, "data": processed_items}
            else:
                return {"success": False, "error": "No products found for this query."}
        else:
            if response.status_code in [403, 401] or "captcha" in response.text.lower() or "slide" in response.text.lower() or "verify" in response.text.lower():
                return {"success": False, "error": "Blocked by Daraz Anti-Bot filter (Captcha/403)."}
            return {"success": False, "error": f"Bad response from Daraz: HTTP {response.status_code}"}
                
    except Exception as e:
        return {"success": False, "error": f"Network exception: {str(e)}"}