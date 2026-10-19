"""
天气预测服务
使用Open-Meteo API提供免费的实时天气数据和预报
参考: travel-ai项目的weather实现方式
"""

import requests
import json
from typing import Optional, Dict, Tuple
from datetime import datetime
import streamlit as st


# =============================================================================
# Weather Code Mappings (from Open-Meteo documentation) - ENGLISH ONLY
# =============================================================================

WEATHER_DESCRIPTIONS = {
    0: 'Clear sky',
    1: 'Mainly clear',
    2: 'Partly cloudy',
    3: 'Overcast',
    45: 'Foggy',
    48: 'Depositing rime fog',
    51: 'Light drizzle',
    53: 'Moderate drizzle',
    55: 'Dense drizzle',
    61: 'Slight rain',
    63: 'Moderate rain',
    65: 'Heavy rain',
    71: 'Slight snow',
    73: 'Moderate snow',
    75: 'Heavy snow',
    77: 'Snow grains',
    80: 'Slight rain showers',
    81: 'Moderate rain showers',
    82: 'Violent rain showers',
    85: 'Slight snow showers',
    86: 'Heavy snow showers',
    95: 'Thunderstorm',
    96: 'Thunderstorm with slight hail',
    99: 'Thunderstorm with heavy hail'
}


# =============================================================================
# Geocoding - Get coordinates from city name
# =============================================================================

@st.cache_data(ttl=86400)
def get_city_coordinates(city_name: str) -> Optional[Tuple[float, float, str, str]]:
    """
    获取城市坐标
    返回: (latitude, longitude, city_name, country_name) 或 None
    """
    try:
        print(f"🌍 正在获取'{city_name}'的坐标...")
        
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en"
        response = requests.get(geocode_url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ 地理编码失败: {response.status_code}")
            return None
        
        data = response.json()
        
        if not data.get('results') or len(data['results']) == 0:
            print(f"❌ 找不到城市: {city_name}")
            return None
        
        result = data['results'][0]
        latitude = result['latitude']
        longitude = result['longitude']
        name = result.get('name', city_name)
        country = result.get('country', '')
        
        print(f"✅ 找到城市: {name}, {country} (纬度: {latitude}, 经度: {longitude})")
        return (latitude, longitude, name, country)
    
    except Exception as e:
        print(f"❌ 地理编码错误: {str(e)}")
        return None


# =============================================================================
# Weather Data Fetching
# =============================================================================

def fetch_weather_data(city_name: str, days: int = 7) -> Optional[Dict]:
    """
    获取实时天气数据和7天预报
    返回包含current和forecast的字典
    """
    try:
        print(f"🌤️ 正在获取'{city_name}'的天气数据...")
        
        # Step 1: Get city coordinates
        coords = get_city_coordinates(city_name)
        if not coords:
            print(f"⚠️ 无法获取{city_name}的坐标，使用模拟天气")
            return None
        
        latitude, longitude, city_name_normalized, country = coords
        
        # Step 2: Fetch weather data from Open-Meteo
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={latitude}&longitude={longitude}"
            f"&current=temperature_2m,relativehumidity_2m,weathercode,windspeed_10m"
            f"&daily=temperature_2m_max,temperature_2m_min,weathercode,precipitation_probability"
            f"&timezone=auto"
        )
        
        response = requests.get(weather_url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ 天气API失败: {response.status_code}")
            return None
        
        weather_data = response.json()
        
        # Process current weather
        current = weather_data['current']
        processed_weather = {
            'location': f"{city_name_normalized}, {country}",
            'latitude': latitude,
            'longitude': longitude,
            'current': {
                'temp': round(current['temperature_2m']),
                'condition': WEATHER_DESCRIPTIONS.get(current['weathercode'], 'Unknown'),
                'humidity': round(current['relativehumidity_2m']),
                'wind': round(current['windspeed_10m']),
                'time': current.get('time', '')
            },
            'forecast': []
        }
        
        # Process daily forecast (7 days)
        daily = weather_data['daily']
        for i, date in enumerate(daily['time']):
            if i >= days:  # Get 7 days
                break
            
            day_name = 'Today' if i == 0 else 'Tomorrow' if i == 1 else f'Day {i+1}'
            
            forecast_day = {
                'date': date,
                'day': day_name,
                'emoji': get_weather_emoji(daily['weathercode'][i]),
                'temp_max': round(daily['temperature_2m_max'][i]),
                'temp_min': round(daily['temperature_2m_min'][i]),
                'temp_avg': round((daily['temperature_2m_max'][i] + daily['temperature_2m_min'][i]) / 2),
                'condition': WEATHER_DESCRIPTIONS.get(daily['weathercode'][i], 'Unknown'),
                'rainfall_probability': daily['precipitation_probability'][i] if i < len(daily['precipitation_probability']) else 0,
                'humidity': 65,  # Average humidity
                'wind_speed': round(10),  # Average wind
                'what_to_wear': get_clothing_recommendation(round((daily['temperature_2m_max'][i] + daily['temperature_2m_min'][i]) / 2)),
                'outdoor_activity_rating': get_activity_rating(daily['weathercode'][i])
            }
            processed_weather['forecast'].append(forecast_day)
        
        print(f"✅ Successfully fetched 7-day weather for {city_name}")
        return processed_weather
    
    except requests.exceptions.Timeout:
        print(f"❌ Request timeout: Cannot connect to weather API")
        return None
    except Exception as e:
        print(f"❌ Error fetching weather data: {str(e)}")
        return None


# =============================================================================
# Weather Helper Functions
# =============================================================================

def get_clothing_recommendation(temp: int) -> str:
    """Get clothing recommendation based on temperature (English only)"""
    if temp > 28:
        return "Light clothing, sunscreen, sunglasses, hat"
    elif temp > 20:
        return "Light layers, comfortable clothing, light jacket"
    elif temp > 15:
        return "Jacket, long sleeves, comfortable pants"
    else:
        return "Warm coat, boots, winter accessories"

def get_activity_rating(weather_code: int) -> int:
    """Get outdoor activity rating based on weather code (1-5)"""
    if weather_code in [0, 1]:  # Clear/Mainly clear
        return 5
    elif weather_code in [2]:  # Partly cloudy
        return 4
    elif weather_code in [3, 45]:  # Overcast/Foggy
        return 3
    elif weather_code in [51, 53, 55, 61, 63, 65]:  # Drizzle/Rain
        return 2
    else:  # Heavy rain/snow/thunderstorm
        return 1

def get_mock_weather(city_name: str) -> Dict:
    """Get mock weather data (fallback when API fails) - 7 days version"""
    return {
        'location': city_name,
        'latitude': 0,
        'longitude': 0,
        'current': {
            'temp': 22,
            'condition': 'Partly Cloudy',
            'humidity': 65,
            'wind': 12,
            'time': ''
        },
        'forecast': [
            {'date': '', 'day': 'Today', 'emoji': '☀️', 'temp_max': 25, 'temp_min': 18, 'temp_avg': 22, 'condition': 'Sunny', 'rainfall_probability': 0, 'humidity': 60, 'wind_speed': 10, 'what_to_wear': 'Light clothing', 'outdoor_activity_rating': 5},
            {'date': '', 'day': 'Tomorrow', 'emoji': '☀️', 'temp_max': 27, 'temp_min': 19, 'temp_avg': 23, 'condition': 'Sunny', 'rainfall_probability': 5, 'humidity': 65, 'wind_speed': 12, 'what_to_wear': 'Light clothing', 'outdoor_activity_rating': 5},
            {'date': '', 'day': 'Day 3', 'emoji': '⛅', 'temp_max': 24, 'temp_min': 17, 'temp_avg': 21, 'condition': 'Partly Cloudy', 'rainfall_probability': 10, 'humidity': 70, 'wind_speed': 15, 'what_to_wear': 'Light layers', 'outdoor_activity_rating': 4},
            {'date': '', 'day': 'Day 4', 'emoji': '☁️', 'temp_max': 26, 'temp_min': 18, 'temp_avg': 22, 'condition': 'Cloudy', 'rainfall_probability': 20, 'humidity': 75, 'wind_speed': 13, 'what_to_wear': 'Light layers', 'outdoor_activity_rating': 3},
            {'date': '', 'day': 'Day 5', 'emoji': '🌧️', 'temp_max': 23, 'temp_min': 16, 'temp_avg': 20, 'condition': 'Rainy', 'rainfall_probability': 70, 'humidity': 85, 'wind_speed': 18, 'what_to_wear': 'Rain jacket', 'outdoor_activity_rating': 2},
            {'date': '', 'day': 'Day 6', 'emoji': '⛅', 'temp_max': 25, 'temp_min': 17, 'temp_avg': 21, 'condition': 'Partly Cloudy', 'rainfall_probability': 15, 'humidity': 68, 'wind_speed': 11, 'what_to_wear': 'Light layers', 'outdoor_activity_rating': 4},
            {'date': '', 'day': 'Day 7', 'emoji': '☀️', 'temp_max': 28, 'temp_min': 20, 'temp_avg': 24, 'condition': 'Sunny', 'rainfall_probability': 0, 'humidity': 60, 'wind_speed': 9, 'what_to_wear': 'Light clothing', 'outdoor_activity_rating': 5}
        ]
    }


def format_weather_for_display(weather_data: Dict) -> str:
    """Format weather data for display (English only)"""
    if not weather_data:
        return "Weather data not available"
    
    current = weather_data['current']
    forecast = weather_data['forecast']
    
    text = f"""
**📍 Location**: {weather_data.get('location', 'N/A')}

**🌡️ Current Weather**:
- Temperature: {current['temp']}°C
- Condition: {current['condition']}
- Humidity: {current['humidity']}%
- Wind Speed: {current['wind']} km/h

**📅 7-Day Forecast**:
"""
    
    for day in forecast:
        text += f"""
- **{day['day']}** ({day['date']}): {day['temp_min']}°C ~ {day['temp_max']}°C, {day['condition']}"""
    
    return text


def get_weather_emoji(weather_code: int) -> str:
    """Return corresponding emoji based on weather code"""
    if weather_code in [0, 1, 2]:
        return "☀️"  # Clear/Sunny
    elif weather_code == 3:
        return "☁️"  # Overcast
    elif weather_code in [45, 48]:
        return "🌫️"  # Foggy
    elif weather_code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
        return "🌧️"  # Rainy
    elif weather_code in [71, 73, 75, 77, 85, 86]:
        return "❄️"  # Snowy
    elif weather_code in [95, 96, 99]:
        return "⛈️"  # Thunderstorm
    else:
        return "🌤️"  # Default


def get_activity_recommendations(weather_data: Dict) -> list:
    """Provide activity recommendations based on weather data (English only)"""
    if not weather_data or not weather_data.get('current'):
        return []
    
    current_temp = weather_data['current']['temp']
    current_condition = weather_data['current']['condition'].lower()
    
    recommendations = []
    
    # Temperature-based recommendations
    if current_temp < 0:
        recommendations.extend(['Skiing', 'Ice Sports', 'Indoor Activities'])
    elif current_temp < 10:
        recommendations.extend(['Hiking', 'Sightseeing', 'Historical Sites Visit'])
    elif current_temp < 20:
        recommendations.extend(['Cycling', 'Walking', 'Outdoor Photography'])
    else:
        recommendations.extend(['Beach', 'Water Sports', 'Park Visit'])
    
    # Weather-based recommendations
    if 'sunny' in current_condition or 'clear' in current_condition:
        recommendations.extend(['Sunset Watching', 'Picnic'])
    elif 'rain' in current_condition or 'drizzle' in current_condition:
        recommendations.extend(['Museum', 'Gallery', 'Shopping'])
    elif 'cloud' in current_condition:
        recommendations.extend(['Temple Visit', 'Cultural Sites'])
    
    return list(set(recommendations))[:5]  # Remove duplicates and limit to 5


# =============================================================================
# Main Weather Service Class
# =============================================================================

class WeatherService:
    """Main weather service class"""
    
    def __init__(self):
        self.cached_weather = {}
    
    def get_weather(self, city_name: str, use_cache: bool = True) -> Dict:
        """
        Get weather for a city.
        
        Args:
            city_name: City name
            use_cache: Whether to use cache
        
        Returns:
            Weather data dictionary
        """
        if use_cache and city_name in self.cached_weather:
            return self.cached_weather[city_name]
        
        weather = fetch_weather_data(city_name)
        
        if not weather:
            weather = get_mock_weather(city_name)
        
        if use_cache:
            self.cached_weather[city_name] = weather
        
        return weather
    
    def get_weather_summary(self, weather_data: Dict, language: str = 'en') -> str:
        """Get weather summary (English only)"""
        return format_weather_for_display(weather_data)


# Create singleton instance
weather_service = WeatherService()
