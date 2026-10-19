import os
"""
酒店推荐器 - Hotel Recommendations Service
使用 Azure OpenAI 生成城市的酒店推荐数据库
"""

import json
from typing import List, Dict, Optional
from openai import AzureOpenAI
import streamlit as st

# =============================================================================
# Azure OpenAI configuration
# =============================================================================

from settings import AZURE_API_KEY  # noqa: E402
AZURE_ENDPOINT = "https://hkust.azure-api.net"
AZURE_DEPLOYMENT_NAME = "gpt-4o-mini"


# =============================================================================
# Hotel Generation using Azure OpenAI
# =============================================================================

def generate_hotels_for_city(city_name: str, country_name: str, api_key: str = AZURE_API_KEY) -> Optional[Dict]:
    """
    使用 Azure OpenAI 生成城市的酒店推荐数据库
    返回包含 budget/mid-range/luxury 酒店的字典
    """
    try:
        print(f"🏨 正在为 {city_name}, {country_name} 生成酒店推荐数据...")
        
        client = AzureOpenAI(
            api_key=api_key,
            api_version="2024-10-21",
            azure_endpoint=AZURE_ENDPOINT,
        )
        
        prompt = f"""Generate hotel recommendations for travelers in {city_name}, {country_name}.

Create 9 hotels: 3 budget, 3 mid-range, 3 luxury.

For EACH hotel, provide JSON with these fields:
{{
  "id": "hotel_slug",
  "name": "Hotel Name",
  "stars": 4,
  "rating": 4.6,
  "review_count": 1250,
  "budget_level": "budget|mid-range|luxury",
  "nightly_rate": "$120",
  "introduction": "Detailed introduction about the hotel's atmosphere, location benefits, and what makes it special. Include information about views, architectural style, and overall experience.",
  "description": "Modern business hotel in central location",
  "amenities": [
    "Free WiFi",
    "24-hour front desk",
    "Breakfast included",
    "Fitness center",
    "Room service"
  ],
  "room_types": {{
    "single": "$100",
    "double": "$120",
    "suite": "$180"
  }},
  "distance_to": {{
    "city_center": "800m, 10 min walk",
    "main_airport": "25km, 45 min by taxi",
    "main_attraction": "2km, 5 min by transit"
  }},
  "why_stay_here": "Great balance of comfort and location for sightseeing",
  "best_for": ["budget travelers", "families", "groups"],
  "highlights": [
    "Popular highlight 1",
    "Popular highlight 2",
    "Popular highlight 3"
  ],
  "guest_reviews": {{
    "positive": "What guests love about this hotel",
    "negative": "Common guest concerns or limitations"
  }},
  "check_in_time": "3:00 PM",
  "check_out_time": "11:00 AM",
  "cancellation_policy": "Free cancellation up to 24 hours",
  "payment_methods": ["Credit card", "PayPal", "Cash"],
  "nearby_restaurants": [
    {{"name": "Restaurant A", "cuisine": "Local", "price_range": "$$"}},
    {{"name": "Restaurant B", "cuisine": "International", "price_range": "$"}}
  ]
}}

Budget hotels: $30-60/night
Mid-range hotels: $80-150/night
Luxury hotels: $200+/night

IMPORTANT: Return ONLY valid JSON array, no markdown, no explanations.
Make it realistic for {city_name} in {country_name}.
Include detailed introductions that sound like TripAdvisor reviews.

[START JSON ARRAY]"""

        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[
                {{
                    "role": "system",
                    "content": "You are a travel accommodation expert. "
                    "Return ONLY valid JSON array, no markdown formatting."
                }},
                {{"role": "user", "content": prompt}},
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Clean up response
        if "[START JSON ARRAY]" in response_text:
            response_text = response_text.split("[START JSON ARRAY]")[-1]
        
        # Extract JSON array
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            hotels = json.loads(json_str)
            
            print(f"✅ 成功为 {city_name} 生成 {len(hotels)} 个酒店推荐")
            
            return {
                'city': city_name,
                'country': country_name,
                'hotels': hotels,
                'total_count': len(hotels),
                'budget_hotels': [h for h in hotels if h.get('budget_level') == 'budget'],
                'midrange_hotels': [h for h in hotels if h.get('budget_level') == 'mid-range'],
                'luxury_hotels': [h for h in hotels if h.get('budget_level') == 'luxury']
            }
        else:
            print(f"❌ 无法解析酒店数据")
            return None
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析错误: {str(e)}")
        # 使用mock数据作为备选
        return get_mock_hotels(city_name, country_name)
    except Exception as e:
        print(f"❌ 生成酒店数据的错误: {str(e)}")
        # 使用mock数据作为备选
        return get_mock_hotels(city_name, country_name)


# =============================================================================
# Mock Hotel Data (Fallback when API fails)
# =============================================================================

def get_mock_hotels(city_name: str, country_name: str) -> Dict:
    """获取Mock酒店数据 - 当API失败时使用"""
    
    mock_hotels_data = {
        'city': city_name,
        'country': country_name,
        'hotels': [
            # Budget hotels
            {
                'id': 'budget_1',
                'name': f'{city_name} Budget Inn',
                'stars': 2,
                'rating': 4.1,
                'review_count': 280,
                'budget_level': 'budget',
                'nightly_rate': '$35-50',
                'description': 'Simple and clean budget hotel, perfect for backpackers',
                'amenities': ['WiFi', 'Basic rooms', 'Shared bathroom', '24-hour front desk'],
                'distance_to': {'city_center': '2km', 'main_airport': '30km'}
            },
            {
                'id': 'budget_2',
                'name': f'Hostel {city_name} Central',
                'stars': 2,
                'rating': 4.3,
                'review_count': 450,
                'budget_level': 'budget',
                'nightly_rate': '$30-45',
                'description': 'Lively hostel with great community atmosphere',
                'amenities': ['Shared dormitory', 'Public kitchen', 'Lounge', 'Free breakfast'],
                'distance_to': {'city_center': '0.5km', 'main_airport': '35km'}
            },
            {
                'id': 'budget_3',
                'name': f'{city_name} Comfort Budget',
                'stars': 2,
                'rating': 4.2,
                'review_count': 320,
                'budget_level': 'budget',
                'nightly_rate': '$40-55',
                'description': 'Affordable accommodation with decent amenities',
                'amenities': ['WiFi', 'Hot shower', 'Air conditioning', 'Basic breakfast'],
                'distance_to': {'city_center': '1.5km', 'main_airport': '28km'}
            },
            # Mid-range hotels
            {
                'id': 'midrange_1',
                'name': f'{city_name} Plaza Hotel',
                'stars': 4,
                'rating': 4.5,
                'review_count': 650,
                'budget_level': 'mid-range',
                'nightly_rate': '$90-130',
                'description': 'Comfortable mid-range hotel with good amenities',
                'amenities': ['WiFi', 'Restaurant', 'Gym', 'Business center', 'Room service'],
                'distance_to': {'city_center': '1km', 'main_airport': '25km'}
            },
            {
                'id': 'midrange_2',
                'name': f'{city_name} Gateway Resort',
                'stars': 3,
                'rating': 4.4,
                'review_count': 580,
                'budget_level': 'mid-range',
                'nightly_rate': '$85-120',
                'description': 'Resort-style hotel with pool and outdoor activities',
                'amenities': ['WiFi', 'Swimming pool', 'Spa', 'Restaurant', 'Parking'],
                'distance_to': {'city_center': '2.5km', 'main_airport': '22km'}
            },
            {
                'id': 'midrange_3',
                'name': f'{city_name} Boutique Hotel',
                'stars': 4,
                'rating': 4.6,
                'review_count': 720,
                'budget_level': 'mid-range',
                'nightly_rate': '$100-150',
                'description': 'Charming boutique hotel with unique decor',
                'amenities': ['WiFi', 'Bar', 'Concierge', 'Luxury amenities', 'City view'],
                'distance_to': {'city_center': '0.8km', 'main_airport': '26km'}
            },
            # Luxury hotels
            {
                'id': 'luxury_1',
                'name': f'{city_name} Grand Palace',
                'stars': 5,
                'rating': 4.8,
                'review_count': 1200,
                'budget_level': 'luxury',
                'nightly_rate': '$280-450',
                'description': 'Ultra-luxury 5-star hotel with premium services',
                'amenities': ['WiFi', 'Fine dining', '24/7 concierge', 'Spa & wellness', 'Executive lounge'],
                'distance_to': {'city_center': '1.2km', 'main_airport': '20km'}
            },
            {
                'id': 'luxury_2',
                'name': f'{city_name} Luxury Suites',
                'stars': 5,
                'rating': 4.7,
                'review_count': 950,
                'budget_level': 'luxury',
                'nightly_rate': '$250-400',
                'description': 'Exclusive suites with personalized service',
                'amenities': ['WiFi', 'Private restaurant', 'Personal butler', 'Rooftop bar', 'Pool'],
                'distance_to': {'city_center': '0.6km', 'main_airport': '24km'}
            },
            {
                'id': 'luxury_3',
                'name': f'{city_name} Heritage Hotel',
                'stars': 5,
                'rating': 4.9,
                'review_count': 1100,
                'budget_level': 'luxury',
                'nightly_rate': '$300-500',
                'description': 'Historic luxury hotel, perfect for experiencing local culture',
                'amenities': ['WiFi', 'Michelin restaurant', 'Library', 'Spa', 'Heritage tours'],
                'distance_to': {'city_center': '1.5km', 'main_airport': '19km'}
            }
        ]
    }
    
    # Set budget_hotels, midrange_hotels, luxury_hotels for easy access
    mock_hotels_data['total_count'] = len(mock_hotels_data['hotels'])
    mock_hotels_data['budget_hotels'] = [h for h in mock_hotels_data['hotels'] if h.get('budget_level') == 'budget']
    mock_hotels_data['midrange_hotels'] = [h for h in mock_hotels_data['hotels'] if h.get('budget_level') == 'mid-range']
    mock_hotels_data['luxury_hotels'] = [h for h in mock_hotels_data['hotels'] if h.get('budget_level') == 'luxury']
    
    print(f"⚠️ 使用Mock酒店数据作为备选 for {city_name}, {country_name}")
    return mock_hotels_data


# =============================================================================
# Display Hotels
# =============================================================================

def format_hotels_for_display(hotels_data: Optional[Dict]) -> str:
    """格式化酒店数据用于Streamlit显示"""
    if not hotels_data:
        return "酒店数据不可用"
    
    output = f"### 🏨 {hotels_data['city']}, {hotels_data['country']} - 酒店推荐 ({hotels_data['total_count']} 个)\n\n"
    
    hotels = hotels_data.get('hotels', [])
    
    # Group by budget level
    budget_hotels = [h for h in hotels if h.get('budget_level') == 'budget']
    midrange_hotels = [h for h in hotels if h.get('budget_level') == 'mid-range']
    luxury_hotels = [h for h in hotels if h.get('budget_level') == 'luxury']
    
    # Display budget hotels
    if budget_hotels:
        output += "#### 💰 预算酒店 (Budget) - $30-60/night\n"
        for hotel in budget_hotels:
            name = hotel.get('name', 'Unknown')
            stars = hotel.get('stars', 0)
            rating = hotel.get('rating', 0)
            nightly_rate = hotel.get('nightly_rate', '$N/A')
            description = hotel.get('description', '')
            
            output += f"\n⭐ **{name}** ({stars}⭐, Rating: {rating}/5.0)\n"
            output += f"   - 💵 {nightly_rate}\n"
            output += f"   - 📝 {description}\n"
    
    # Display mid-range hotels
    if midrange_hotels:
        output += "\n\n#### 🏩 中档酒店 (Mid-range) - $80-150/night\n"
        for hotel in midrange_hotels:
            name = hotel.get('name', 'Unknown')
            stars = hotel.get('stars', 0)
            rating = hotel.get('rating', 0)
            nightly_rate = hotel.get('nightly_rate', '$N/A')
            description = hotel.get('description', '')
            
            output += f"\n⭐ **{name}** ({stars}⭐, Rating: {rating}/5.0)\n"
            output += f"   - 💵 {nightly_rate}\n"
            output += f"   - 📝 {description}\n"
    
    # Display luxury hotels
    if luxury_hotels:
        output += "\n\n#### 👑 豪华酒店 (Luxury) - $200+/night\n"
        for hotel in luxury_hotels:
            name = hotel.get('name', 'Unknown')
            stars = hotel.get('stars', 0)
            rating = hotel.get('rating', 0)
            nightly_rate = hotel.get('nightly_rate', '$N/A')
            description = hotel.get('description', '')
            
            output += f"\n⭐ **{name}** ({stars}⭐, Rating: {rating}/5.0)\n"
            output += f"   - 💵 {nightly_rate}\n"
            output += f"   - 📝 {description}\n"
    
    return output


def get_hotels_summary(hotels_data: Optional[Dict]) -> Dict:
    """获取酒店总结统计"""
    if not hotels_data:
        return {
            'budget_count': 0,
            'midrange_count': 0,
            'luxury_count': 0,
            'avg_rating': 0
        }
    
    hotels = hotels_data.get('hotels', [])
    
    return {
        'budget_count': len(hotels_data.get('budget_hotels', [])),
        'midrange_count': len(hotels_data.get('midrange_hotels', [])),
        'luxury_count': len(hotels_data.get('luxury_hotels', [])),
        'avg_rating': round(sum([h.get('rating', 0) for h in hotels]) / len(hotels), 2) if hotels else 0,
        'total_count': len(hotels)
    }
