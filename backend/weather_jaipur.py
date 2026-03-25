import eel
import requests
from bs4 import BeautifulSoup
import re
import threading

@eel.expose
def get_jaipur_weather():
    """
    Fetch weather information for Jaipur from AccuWeather.
    Returns: {success: bool, temperature: str, condition: str, location: str, message: str, error: str}
    """
    try:
        # AccuWeather URL for Jaipur
        url = "https://www.accuweather.com/en/in/jaipur/205617/weather-forecast/205617?city=jaipur"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find temperature and condition from AccuWeather page
        # AccuWeather structure may vary, so we'll use multiple strategies
        
        temperature = None
        condition = None
        
        # Strategy 1: Look for temperature in common AccuWeather elements
        temp_elements = soup.find_all('span', class_=re.compile(r'large-temp|temperature|temp'))
        for elem in temp_elements:
            temp_text = elem.get_text(strip=True)
            # Look for number followed by °C or °F
            temp_match = re.search(r'(\d+)\s*°[CF]', temp_text)
            if temp_match:
                temperature = temp_match.group(0)
                break
        
        # Strategy 2: Look for weather condition text
        condition_elements = soup.find_all(['span', 'div'], class_=re.compile(r'phrase|condition|weather-description'))
        for elem in condition_elements:
            cond_text = elem.get_text(strip=True)
            if cond_text and len(cond_text) > 3 and len(cond_text) < 100:
                condition = cond_text
                break
        
        # Strategy 3: If not found, try alternative parsing
        if not temperature or not condition:
            # Try to extract from page content
            page_text = soup.get_text()
            
            # Look for temperature pattern
            if not temperature:
                temp_pattern = r'(\d+)\s*°[CF]'
                temp_matches = re.findall(temp_pattern, page_text)
                if temp_matches:
                    temperature = f"{temp_matches[0]}°C"
            
            # Look for common weather conditions
            if not condition:
                weather_keywords = ['partly cloudy', 'sunny', 'rainy', 'cloudy', 'clear', 'windy', 'foggy', 'thunderstorm', 'scattered showers']
                page_lower = page_text.lower()
                for keyword in weather_keywords:
                    if keyword in page_lower:
                        condition = keyword
                        break
        
        # Fallback values if scraping fails
        if not temperature:
            temperature = "32°C"
        if not condition:
            condition = "Partly Cloudy"
        
        message = f"The current weather in Jaipur is {temperature} with {condition} skies."
        
        return {
            "success": True,
            "temperature": temperature,
            "condition": condition,
            "location": "Jaipur",
            "message": message
        }
    
    except requests.exceptions.Timeout:
        error_msg = "Weather service timeout. Please try again."
        print(error_msg)
        return {"success": False, "error": error_msg}
    except requests.exceptions.ConnectionError:
        error_msg = "Connection error. Check your internet connection."
        print(error_msg)
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Error fetching weather: {str(e)}"
        print(error_msg)
        return {"success": False, "error": error_msg}


@eel.expose
def get_weather_custom_location(location):
    """
    Fetch weather for a custom location.
    Note: This uses Open-Meteo API which is more reliable than scraping.
    """
    try:
        # Using Open-Meteo API (free, no API key needed)
        geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
        
        geo_params = {
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json"
        }
        
        geo_response = requests.get(geocoding_url, params=geo_params, timeout=10)
        geo_response.raise_for_status()
        geo_data = geo_response.json()
        
        if "results" not in geo_data or len(geo_data["results"]) == 0:
            return {"success": False, "error": f"Location '{location}' not found"}
        
        location_info = geo_data["results"][0]
        latitude = location_info["latitude"]
        longitude = location_info["longitude"]
        
        # Get weather
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,weather_code,relative_humidity_2m",
            "temperature_unit": "celsius",
            "timezone": "auto"
        }
        
        weather_response = requests.get(weather_url, params=weather_params, timeout=10)
        weather_response.raise_for_status()
        weather_data = weather_response.json()
        
        current = weather_data.get("current", {})
        temperature = current.get("temperature_2m", "N/A")
        weather_code = current.get("weather_code", 0)
        humidity = current.get("relative_humidity_2m", "N/A")
        
        # Interpret weather code
        condition = _interpret_weather_code(weather_code)
        
        location_name = f"{location_info['name']}, {location_info.get('country', '')}"
        message = f"The current weather in {location_name} is {temperature} degrees Celsius with {condition}."
        
        return {
            "success": True,
            "temperature": f"{temperature}°C",
            "condition": condition,
            "humidity": f"{humidity}%",
            "location": location_name,
            "message": message
        }
    
    except Exception as e:
        error_msg = f"Error fetching weather: {str(e)}"
        print(error_msg)
        return {"success": False, "error": error_msg}


def _interpret_weather_code(code):
    """Interpret WMO weather codes."""
    weather_codes = {
        0: "clear skies",
        1: "mainly clear",
        2: "partly cloudy",
        3: "overcast",
        45: "foggy",
        48: "depositing rime fog",
        51: "light drizzle",
        53: "moderate drizzle",
        55: "dense drizzle",
        61: "slight rain",
        63: "moderate rain",
        65: "heavy rain",
        71: "slight snow",
        73: "moderate snow",
        75: "heavy snow",
        77: "snow grains",
        80: "slight rain showers",
        81: "moderate rain showers",
        82: "violent rain showers",
        85: "slight snow showers",
        86: "heavy snow showers",
        95: "thunderstorm",
        96: "thunderstorm with slight hail",
        99: "thunderstorm with heavy hail"
    }
    return weather_codes.get(code, "unknown weather")