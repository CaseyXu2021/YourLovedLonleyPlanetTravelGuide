"""
天气服务测试脚本
Test the weather service independently
"""

import sys
from pathlib import Path
from weather_service import (
    weather_service, 
    fetch_weather_data,
    get_activity_recommendations,
    get_weather_emoji,
    format_weather_for_display
)

def test_weather_service():
    """Test the weather service with sample cities"""
    
    print("\n" + "="*60)
    print("🌤️  天气服务测试 (Weather Service Testing)")
    print("="*60 + "\n")
    
    # Test cities
    test_cities = [
        "Paris",
        "Tokyo",
        "London",
        "Bangkok",
        "New York"
    ]
    
    for city in test_cities:
        print(f"\n📍 Testing: {city}")
        print("-" * 40)
        
        try:
            # Get weather
            weather = weather_service.get_weather(city)
            
            if weather:
                # Display formatted weather
                print(format_weather_for_display(weather))
                
                # Get activity recommendations
                activities = get_activity_recommendations(weather)
                if activities:
                    print("\n🎯 推荐活动 (Recommended Activities):")
                    for activity in activities:
                        print(f"   • {activity}")
                
                # Show forecast emoji
                print("\n📅 天气emoji (Weather Emoji):")
                for day in weather['forecast'][:3]:
                    emoji = get_weather_emoji(day['condition'])
                    print(f"   {emoji} {day['day']}: {day['condition']}")
                
                print("\n✅ Success!")
            else:
                print("❌ Failed to get weather data")
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print()
    
    print("\n" + "="*60)
    print("✅ 测试完成 (Testing Complete)")
    print("="*60)


def test_api_connectivity():
    """Test API connectivity"""
    print("\n" + "="*60)
    print("🌐 API 连接性测试 (API Connectivity Testing)")
    print("="*60 + "\n")
    
    import requests
    
    apis = [
        ("Open-Meteo Weather API", "https://api.open-meteo.com/v1/forecast?latitude=48.8566&longitude=2.3522&current=temperature_2m"),
        ("Open-Meteo Geocoding API", "https://geocoding-api.open-meteo.com/v1/search?name=Paris&count=1"),
    ]
    
    for name, url in apis:
        try:
            print(f"Testing: {name}")
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: Connected")
            else:
                print(f"❌ {name}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ {name}: {str(e)}")
    
    print()


if __name__ == "__main__":
    print("\n🌍 开始天气服务测试 (Starting Weather Service Testing)\n")
    
    # Test API connectivity
    test_api_connectivity()
    
    # Test weather service
    test_weather_service()
    
    print("\n💡 提示 (Tips):")
    print("1. 确保您的网络连接正常")
    print("2. Open-Meteo API 完全免费，无需API密钥")
    print("3. 第一次请求可能较慢，结果会被缓存24小时")
    print("4. 在Streamlit应用中，使用 weather_service.get_weather() 获取数据\n")
