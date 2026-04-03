import cloudscraper
import json

def get_best_daraz_deal(query: str):
    """
    Fetches the top product from Daraz for a given query.
    Returns a dictionary indicating success and either data or error.
    """
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "desktop": True}
    )

    # Use the AJAX API endpoint for better reliability and JSON response
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
                return {"success": True, "data": items[0]}
            else:
                return {"success": False, "error": "No products found for this query."}
        else:
            # Check if it was an anti-bot page or generic failure
            if response.status_code in [403, 401] or "captcha" in response.text.lower() or "slide" in response.text.lower() or "verify" in response.text.lower():
                return {"success": False, "error": "Blocked by Daraz Anti-Bot filter (Captcha/403)."}
            return {"success": False, "error": f"Bad response from Daraz: HTTP {response.status_code}"}
                
    except Exception as e:
        return {"success": False, "error": f"Network exception: {str(e)}"}