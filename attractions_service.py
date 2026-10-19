import os
"""
景点评分推荐器 - Attractions Rating & Recommendations Service
使用 Azure OpenAI 生成城市景点评分和评价数据库
参考: Lonely Planet 景点权重评分体系
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
# Attractions Generation using Azure OpenAI
# =============================================================================

def generate_attractions_for_city(city_name: str, country_name: str, api_key: str = AZURE_API_KEY) -> Optional[Dict]:
    """
    使用 Azure OpenAI 生成城市的景点评分数据库
    返回包含 top/medium/worst 景点的字典
    """
    try:
        print(f"🎭 正在为 {city_name}, {country_name} 生成景点评分数据...")
        
        client = AzureOpenAI(
            api_key=api_key,
            api_version="2024-10-21",
            azure_endpoint=AZURE_ENDPOINT,
        )
        
        prompt = f"""Generate comprehensive attractions database for {city_name}, {country_name}.

For EACH attraction, provide JSON with these fields:
{{
  "id": "unique_slug",
  "name": "Full Name",
  "rating": 4.7,
  "review_count": 3421,
  "emoji": "🎭",
  "type": "top|medium|worst",
  "category": "culture|nature|food|shopping|nightlife|adventure|museum|temple",
  "description": "1-sentence description",
  "why_popular": "What makes it special",
  "typical_visitor_duration": "2-3 hours",
  "entry_fee": "$12-15 USD",
  "operating_hours": "9:00 AM - 5:00 PM daily",
  "best_time_to_visit": "Early morning (8:00-9:30)",
  "how_to_get_there": "Transit description",
  "nearby_food": ["Restaurant 1", "Restaurant 2"],
  "pro_tips": ["Tip 1", "Tip 2"],
  "booking_platforms": [
    {{"name": "Google Maps", "available": true}},
    {{"name": "Klook", "available": true}},
    {{"name": "Viator", "available": false}}
  ],
  "accessibility": "Wheelchair accessible / Limited"
}}

Create 15-20 attractions including:
- 4-5 must-see landmarks (rating 4.6+, type: "top")
- 3-4 hidden gems (rating 4.3-4.5, type: "medium")
- 2-3 food/dining experiences (rating 4.5+)
- 1-2 shopping areas (rating 4.2+)
- 1-2 nightlife spots (rating 4.2+)
- 2-3 tourist traps to avoid (rating 2.0-3.0, type: "worst")

IMPORTANT: Return ONLY valid JSON array, no markdown, no explanations.
Make it realistic for {city_name} in {country_name}.

[START JSON ARRAY]"""

        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[
                {{
                    "role": "system",
                    "content": "You are a travel expert who generates authentic attraction databases. "
                    "Return ONLY valid JSON, no markdown formatting, no code blocks. Return a JSON array."
                }},
                {{"role": "user", "content": prompt}},
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Clean up the response to extract JSON
        if "[START JSON ARRAY]" in response_text:
            response_text = response_text.split("[START JSON ARRAY]")[-1]
        
        # Try to extract JSON array
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            attractions = json.loads(json_str)
            
            print(f"✅ 成功为 {city_name} 生成 {len(attractions)} 个景点")
            return {
                'city': city_name,
                'country': country_name,
                'attractions': attractions,
                'total_count': len(attractions),
                'top_attractions': [a for a in attractions if a.get('type') == 'top'][:4],
                'worst_attractions': [a for a in attractions if a.get('type') == 'worst']
            }
        else:
            print(f"❌ 无法解析景点数据")
            return None
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析错误: {str(e)}")
        # 使用mock数据作为备选
        return get_mock_attractions(city_name, country_name)
    except Exception as e:
        print(f"❌ 生成景点数据的错误: {str(e)}")
        # 使用mock数据作为备选
        return get_mock_attractions(city_name, country_name)


# =============================================================================
# Mock Attractions Data (Fallback when API fails)
# =============================================================================

def get_mock_attractions(city_name: str, country_name: str) -> Dict:
    """获取Mock景点数据 - 当API失败时使用"""
    
    mock_attractions = [
        # Top attractions
        {
            'id': 'top_1', 'name': f'{city_name} Historic Center',
            'rating': 4.7, 'review_count': 2340, 'emoji': '🏛️', 'type': 'top',
            'category': 'culture', 'description': 'Historic city center with heritage buildings',
            'why_popular': 'UNESCO World Heritage site with stunning architecture',
            'typical_visitor_duration': '2-3 hours', 'entry_fee': 'Free',
            'operating_hours': '9:00 AM - 5:00 PM daily'
        },
        {
            'id': 'top_2', 'name': f'{city_name} Central Museum',
            'rating': 4.6, 'review_count': 1890, 'emoji': '🏺', 'type': 'top',
            'category': 'museum', 'description': 'Main museum with art and history collections',
            'why_popular': 'One of the most comprehensive collections in the region',
            'typical_visitor_duration': '2-4 hours', 'entry_fee': '$12-15',
            'operating_hours': '10:00 AM - 6:00 PM'
        },
        {
            'id': 'top_3', 'name': f'{city_name} Main Market',
            'rating': 4.5, 'review_count': 3100, 'emoji': '🛍️', 'type': 'top',
            'category': 'shopping', 'description': 'Vibrant traditional market with local goods',
            'why_popular': 'Best place to experience local culture and buy souvenirs',
            'typical_visitor_duration': '1-2 hours', 'entry_fee': 'Free',
            'operating_hours': '6:00 AM - 7:00 PM daily'
        },
        {
            'id': 'top_4', 'name': f'{city_name} Nature Park',
            'rating': 4.8, 'review_count': 2560, 'emoji': '🌳', 'type': 'top',
            'category': 'nature', 'description': 'Large urban park with hiking trails',
            'why_popular': 'Perfect escape from city with scenic viewpoints',
            'typical_visitor_duration': '2-3 hours', 'entry_fee': 'Free',
            'operating_hours': '7:00 AM - 9:00 PM daily'
        },
        # Medium attractions
        {
            'id': 'med_1', 'name': f'{city_name} Food Festival Street',
            'rating': 4.4, 'review_count': 1450, 'emoji': '🍜', 'type': 'medium',
            'category': 'food', 'description': 'Street filled with local food vendors',
            'why_popular': 'Authentic local cuisine at affordable prices',
            'typical_visitor_duration': '1-2 hours', 'entry_fee': 'Free',
            'operating_hours': '11:00 AM - 11:00 PM'
        },
        {
            'id': 'med_2', 'name': f'{city_name} Nightlife District',
            'rating': 4.3, 'review_count': 980, 'emoji': '🍹', 'type': 'medium',
            'category': 'nightlife', 'description': 'Trendy bars and clubs area',
            'why_popular': 'Lively atmosphere with international and local drinks',
            'typical_visitor_duration': '3-4 hours', 'entry_fee': 'Free (drinks separate)',
            'operating_hours': '8:00 PM - 4:00 AM'
        },
        # Worst attractions (tourist traps)
        {
            'id': 'bad_1', 'name': f'{city_name} Tourist Trap Restaurant',
            'rating': 2.8, 'review_count': 340, 'emoji': '❌', 'type': 'worst',
            'category': 'food', 'description': 'Overpriced tourist-oriented restaurant',
            'why_popular': 'Not recommended - poor quality for high prices',
            'typical_visitor_duration': '1 hour', 'entry_fee': '$30+ per person',
            'operating_hours': '11:00 AM - 10:00 PM'
        },
        {
            'id': 'bad_2', 'name': f'{city_name} Souvenir Alley',
            'rating': 2.5, 'review_count': 200, 'emoji': '❌', 'type': 'worst',
            'category': 'shopping', 'description': 'Overpriced low-quality souvenirs',
            'why_popular': 'Not recommended - inflated prices and poor quality',
            'typical_visitor_duration': '30 minutes', 'entry_fee': 'Free',
            'operating_hours': '9:00 AM - 8:00 PM'
        }
    ]
    
    return {
        'city': city_name,
        'country': country_name,
        'attractions': mock_attractions,
        'total_count': len(mock_attractions),
        'top_attractions': [a for a in mock_attractions if a.get('type') == 'top'][:4],
        'worst_attractions': [a for a in mock_attractions if a.get('type') == 'worst']
    }


# =============================================================================
# Display Attractions
# =============================================================================

def format_attractions_for_display(attractions_data: Optional[Dict]) -> str:
    """格式化景点数据用于Streamlit显示"""
    if not attractions_data:
        return "景点数据不可用"
    
    output = f"### 🎭 {attractions_data['city']}, {attractions_data['country']} - 景点评分 ({attractions_data['total_count']} 个)\n\n"
    
    attractions = attractions_data.get('attractions', [])
    
    # Sort by type and rating
    top_attractions = [a for a in attractions if a.get('type') == 'top']
    medium_attractions = [a for a in attractions if a.get('type') == 'medium']
    worst_attractions = [a for a in attractions if a.get('type') == 'worst']
    
    # Display top attractions
    if top_attractions:
        output += "#### ⭐ 必看景点 (Must-See)\n"
        for attr in sorted(top_attractions, key=lambda x: x.get('rating', 0), reverse=True)[:5]:
            emoji = attr.get('emoji', '📍')
            name = attr.get('name', 'Unknown')
            rating = attr.get('rating', 0)
            review_count = attr.get('review_count', 0)
            description = attr.get('description', '')
            duration = attr.get('typical_visitor_duration', '2 hours')
            fee = attr.get('entry_fee', 'Free')
            
            output += f"\n{emoji} **{name}** ⭐ {rating}/5.0 ({review_count:,} reviews)\n"
            output += f"   - {description}\n"
            output += f"   - ⏱️ 建议耗时: {duration} | 💰 入场费: {fee}\n"
            output += f"   - 💡 {attr.get('why_popular', 'Popular attraction')}\n"
    
    # Display hidden gems
    if medium_attractions:
        output += "\n\n#### 💎 隐藏宝石 (Hidden Gems)\n"
        for attr in sorted(medium_attractions, key=lambda x: x.get('rating', 0), reverse=True)[:3]:
            emoji = attr.get('emoji', '📍')
            name = attr.get('name', 'Unknown')
            rating = attr.get('rating', 0)
            description = attr.get('description', '')
            
            output += f"\n{emoji} **{name}** ⭐ {rating}/5.0\n"
            output += f"   - {description}\n"
    
    # Display worst attractions
    if worst_attractions:
        output += "\n\n#### ⚠️ 需要避免的景点 (Tourist Traps)\n"
        for attr in worst_attractions[:2]:
            emoji = attr.get('emoji', '🚫')
            name = attr.get('name', 'Unknown')
            rating = attr.get('rating', 0)
            reason = attr.get('why_popular', 'Avoid this place')
            
            output += f"\n{emoji} **{name}** ⭐ {rating}/5.0\n"
            output += f"   - ⚠️ {reason}\n"
    
    return output


def get_attractions_summary(attractions_data: Optional[Dict]) -> Dict:
    """获取景点总结统计"""
    if not attractions_data:
        return {
            'top_count': 0,
            'medium_count': 0,
            'worst_count': 0,
            'avg_rating': 0
        }
    
    attractions = attractions_data.get('attractions', [])
    
    return {
        'top_count': len([a for a in attractions if a.get('type') == 'top']),
        'medium_count': len([a for a in attractions if a.get('type') == 'medium']),
        'worst_count': len([a for a in attractions if a.get('type') == 'worst']),
        'avg_rating': round(sum([a.get('rating', 0) for a in attractions]) / len(attractions), 2) if attractions else 0,
        'total_count': len(attractions)
    }
