import requests
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

def get_weather(city: str) -> dict:
    """Fetch complete weather information from OpenWeatherMap."""
    api_key = Config.OPENWEATHERMAP_API_KEY
    if not api_key:
        return {"success": False, "error": "OpenWeatherMap API Key is not configured in .env"}
        
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "temp": data["main"]["temp"],
                "description": data["weather"][0]["description"].title(),
                "city": data["name"],
                "country": data["sys"]["country"]
            }
        elif response.status_code == 404:
            return {"success": False, "error": f"City '{city}' not found."}
        elif response.status_code == 401:
            return {"success": False, "error": "Invalid OpenWeatherMap API Key."}
        else:
            return {"success": False, "error": f"API returned HTTP {response.status_code}"}
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return {"success": False, "error": f"Network error occurred."}
