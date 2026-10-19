import os
"""
Top Rated Restaurants Service - Restaurant Recommendations with Reviews
Generates AI-powered restaurant database with ratings and Google-style reviews
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
# Restaurant Generation using Azure OpenAI
# =============================================================================

def generate_restaurants_for_city(city_name: str, country_name: str, api_key: str = AZURE_API_KEY) -> Optional[Dict]:
    """
    Generate top-rated restaurants for a city using Azure OpenAI.
    Returns dict with restaurants grouped by cuisine type and ratings.
    """
    try:
        print(f"🍽️ Generating restaurants for {city_name}, {country_name}...")
        
        client = AzureOpenAI(
            api_key=api_key,
            api_version="2024-10-21",
            azure_endpoint=AZURE_ENDPOINT,
        )
        
        prompt = f"""Generate top-rated restaurants for {city_name}, {country_name}.

Create 12 restaurants: 3 budget/casual, 3 mid-range, 3 fine dining, 3 specialty/unique.

For EACH restaurant, provide JSON with these fields:
{{
  "id": "restaurant_slug",
  "name": "Restaurant Name",
  "cuisine_type": "Italian|Thai|Japanese|Local|Fusion|etc",
  "price_level": "$|$$|$$$|$$$$",
  "rating": 4.7,
  "review_count": 1250,
  "category": "budget|mid-range|fine_dining|specialty",
  "address": "Street address",
  "phone": "+1-XXX-XXX-XXXX",
  "average_cost_per_person": "$15-25 USD",
  "description": "One-line description of the restaurant",
  "specialties": ["Signature dish 1", "Signature dish 2", "Specialty 3"],
  "dining_style": "Casual|Smart Casual|Fine Dining|Counter Seating",
  "opening_hours": "11:00 AM - 11:00 PM",
  "reservation_recommended": true,
  "google_reviews": [
    {{
      "reviewer_name": "John D.",
      "rating": 5,
      "date": "2 weeks ago",
      "review_text": "Amazing experience! The food was incredible and service was excellent."
    }},
    {{
      "reviewer_name": "Sarah M.",
      "rating": 4,
      "date": "1 month ago",
      "review_text": "Great restaurant, a bit pricey but worth it."
    }},
    {{
      "reviewer_name": "David L.",
      "rating": 5,
      "date": "3 weeks ago",
      "review_text": "Best meal in town. Highly recommend."
    }}
  ],
  "highlights": [
    "Intimate ambiance",
    "Outdoor seating",
    "Private rooms available",
    "Extensive wine collection"
  ],
  "dietary_options": ["Vegetarian", "Vegan", "Gluten-free"],
  "parking": "Street parking available",
  "why_visit": "Must-try restaurant for authentic local cuisine",
  "best_dishes": [
    {{"name": "Signature Pasta", "price": "$18", "rating": 4.9}},
    {{"name": "Fresh Seafood", "price": "$25", "rating": 4.8}},
    {{"name": "Homemade Dessert", "price": "$8", "rating": 4.7}}
  ],
  "booking_url": "https://www.google.com/maps/search/restaurant+name",
  "map_coordinates": {{
    "latitude": 13.7563,
    "longitude": 100.5018
  }}
}}

Budget: $10-20/person
Mid-range: $20-40/person
Fine Dining: $40-100+/person
Specialty: Varies

IMPORTANT: Return ONLY valid JSON array, no markdown, no explanations.
Make it realistic and authentic for {city_name} in {country_name}.
Include 3 Google-style reviews for EACH restaurant.

[START JSON ARRAY]"""

        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[
                {{
                    "role": "system",
                    "content": "You are a food critic and travel expert. "
                    "Return ONLY valid JSON array, no markdown formatting."
                }},
                {{"role": "user", "content": prompt}},
            ],
            temperature=0.7,
            max_tokens=3000,
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
            restaurants = json.loads(json_str)
            
            print(f"✅ Successfully generated {len(restaurants)} restaurants for {city_name}")
            
            return {
                'city': city_name,
                'country': country_name,
                'restaurants': restaurants,
                'total_count': len(restaurants),
                'budget_restaurants': [r for r in restaurants if r.get('category') == 'budget'],
                'midrange_restaurants': [r for r in restaurants if r.get('category') == 'mid-range'],
                'fine_dining': [r for r in restaurants if r.get('category') == 'fine_dining'],
                'specialty_restaurants': [r for r in restaurants if r.get('category') == 'specialty']
            }
        else:
            print(f"❌ Could not parse restaurant data")
            return None
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {str(e)}")
        return get_mock_restaurants(city_name, country_name)
    except Exception as e:
        print(f"❌ Error generating restaurants: {str(e)}")
        return get_mock_restaurants(city_name, country_name)


# =============================================================================
# Mock Restaurant Data (Fallback when API fails)
# =============================================================================

def get_mock_restaurants(city_name: str, country_name: str) -> Dict:
    """Get mock restaurant data - fallback for API failures"""
    
    mock_restaurants = {
        'city': city_name,
        'country': country_name,
        'restaurants': [
            # Budget restaurants
            {
                'id': 'budget_1',
                'name': f'{city_name} Street Food House',
                'cuisine_type': 'Local',
                'price_level': '$',
                'rating': 4.5,
                'review_count': 380,
                'category': 'budget',
                'address': 'Central Market Area',
                'average_cost_per_person': '$5-12 USD',
                'description': 'Authentic local street food and traditional dishes',
                'specialties': ['Street Noodles', 'Local Rice Bowls', 'Fresh Spring Rolls'],
                'google_reviews': [
                    {
                        'reviewer_name': 'Tom K.',
                        'rating': 5,
                        'date': '1 week ago',
                        'review_text': 'Amazing street food! Authentic and delicious.'
                    },
                    {
                        'reviewer_name': 'Lisa M.',
                        'rating': 4,
                        'date': '2 weeks ago',
                        'review_text': 'Great value for money, friendly staff.'
                    }
                ],
                'best_dishes': [
                    {'name': 'Pad Thai', 'price': '$3-5', 'rating': 4.8},
                    {'name': 'Spring Rolls', 'price': '$2-3', 'rating': 4.6}
                ]
            },
            # Mid-range restaurants
            {
                'id': 'midrange_1',
                'name': f'{city_name} Fusion Kitchen',
                'cuisine_type': 'Fusion',
                'price_level': '$$',
                'rating': 4.6,
                'review_count': 520,
                'category': 'mid-range',
                'address': 'Downtown District',
                'average_cost_per_person': '$15-30 USD',
                'description': 'Modern fusion cuisine combining traditional and contemporary flavors',
                'specialties': ['Fusion Tacos', 'Asian-Western Bowls', 'Creative Cocktails'],
                'google_reviews': [
                    {
                        'reviewer_name': 'Alex J.',
                        'rating': 5,
                        'date': '3 days ago',
                        'review_text': 'Best fusion food in town! Creative and delicious.'
                    },
                    {
                        'reviewer_name': 'Emma R.',
                        'rating': 4,
                        'date': '1 week ago',
                        'review_text': 'Great atmosphere and unique menu.'
                    }
                ],
                'best_dishes': [
                    {'name': 'Fusion Tacos', 'price': '$12-15', 'rating': 4.7},
                    {'name': 'Dragon Bowl', 'price': '$14-18', 'rating': 4.8}
                ]
            },
            # Fine dining
            {
                'id': 'finedining_1',
                'name': f'{city_name} Grand Restaurant',
                'cuisine_type': 'French',
                'price_level': '$$$',
                'rating': 4.8,
                'review_count': 650,
                'category': 'fine_dining',
                'address': 'Luxury Hotel District',
                'average_cost_per_person': '$60-120 USD',
                'description': 'Sophisticated French cuisine with elegant ambiance',
                'specialties': ['Classic French Dishes', 'Fine Wine Pairing', 'Michelin-style Presentation'],
                'google_reviews': [
                    {
                        'reviewer_name': 'Michael P.',
                        'rating': 5,
                        'date': '5 days ago',
                        'review_text': 'Exceptional dining experience. Perfect for special occasions.'
                    },
                    {
                        'reviewer_name': 'Victoria L.',
                        'rating': 5,
                        'date': '1 week ago',
                        'review_text': 'Outstanding food and impeccable service.'
                    }
                ],
                'best_dishes': [
                    {'name': 'Duck Confit', 'price': '$45-55', 'rating': 4.9},
                    {'name': 'Beef Bourguignon', 'price': '$48-58', 'rating': 4.8}
                ]
            },
            # Specialty restaurant
            {
                'id': 'specialty_1',
                'name': f'{city_name} Rooftop Sky Bar & Grill',
                'cuisine_type': 'International',
                'price_level': '$$$',
                'rating': 4.7,
                'review_count': 720,
                'category': 'specialty',
                'address': 'Rooftop, Central Tower',
                'average_cost_per_person': '$40-80 USD',
                'description': 'International cuisine with stunning city views from rooftop',
                'specialties': ['Grilled Prime Cuts', 'Sunset Cocktails', 'Panoramic City Views'],
                'google_reviews': [
                    {
                        'reviewer_name': 'Chris W.',
                        'rating': 5,
                        'date': '2 days ago',
                        'review_text': 'Amazing views and great food! Perfect for proposals.'
                    },
                    {
                        'reviewer_name': 'Rachel T.',
                        'rating': 4,
                        'date': '1 week ago',
                        'review_text': 'Beautiful setting, good cocktails and steaks.'
                    }
                ],
                'best_dishes': [
                    {'name': 'Prime Ribeye Steak', 'price': '$50-65', 'rating': 4.9},
                    {'name': 'Signature Cocktail', 'price': '$15-18', 'rating': 4.7}
                ]
            }
        ]
    }
    
    # Set counts
    mock_restaurants['total_count'] = len(mock_restaurants['restaurants'])
    mock_restaurants['budget_restaurants'] = [r for r in mock_restaurants['restaurants'] if r.get('category') == 'budget']
    mock_restaurants['midrange_restaurants'] = [r for r in mock_restaurants['restaurants'] if r.get('category') == 'mid-range']
    mock_restaurants['fine_dining'] = [r for r in mock_restaurants['restaurants'] if r.get('category') == 'fine_dining']
    mock_restaurants['specialty_restaurants'] = [r for r in mock_restaurants['restaurants'] if r.get('category') == 'specialty']
    
    print(f"⚠️ Using mock restaurant data for {city_name}, {country_name}")
    return mock_restaurants


# =============================================================================
# Display Restaurants with Google-style Reviews
# =============================================================================

def format_restaurants_for_display(restaurants_data: Optional[Dict]) -> str:
    """Format restaurant data for Streamlit display with review cards"""
    if not restaurants_data:
        return "Restaurant data not available"
    
    output = f"\n### 🍽️ Top-Rated Restaurants in {restaurants_data['city']}, {restaurants_data['country']}"
    output += f" ({restaurants_data['total_count']} shown)\n"
    
    restaurants = restaurants_data.get('restaurants', [])
    
    # Group by category
    budget = [r for r in restaurants if r.get('category') == 'budget']
    midrange = [r for r in restaurants if r.get('category') == 'mid-range']
    finedining = [r for r in restaurants if r.get('category') == 'fine_dining']
    specialty = [r for r in restaurants if r.get('category') == 'specialty']
    
    if budget:
        output += "\n#### 💰 Budget-Friendly\n"
        for r in budget:
            output += f"- **{r['name']}** ⭐ {r['rating']}/5 ({r['review_count']} reviews)\n"
            output += f"  {r['description']}\n"
    
    if midrange:
        output += "\n#### 🍴 Mid-Range\n"
        for r in midrange:
            output += f"- **{r['name']}** ⭐ {r['rating']}/5 ({r['review_count']} reviews)\n"
            output += f"  {r['description']}\n"
    
    if finedining:
        output += "\n#### 👑 Fine Dining\n"
        for r in finedining:
            output += f"- **{r['name']}** ⭐ {r['rating']}/5 ({r['review_count']} reviews)\n"
            output += f"  {r['description']}\n"
    
    if specialty:
        output += "\n#### ⭐ Specialty & Unique\n"
        for r in specialty:
            output += f"- **{r['name']}** ⭐ {r['rating']}/5 ({r['review_count']} reviews)\n"
            output += f"  {r['description']}\n"
    
    return output


def display_restaurant_detail_card(restaurant: Dict):
    """Display a single restaurant with detailed info and reviews (for Streamlit)"""
    import streamlit as st
    
    # Color coding by rating
    if restaurant['rating'] >= 4.7:
        color = "#2ecc71"  # Green - Excellent
    elif restaurant['rating'] >= 4.3:
        color = "#3498db"  # Blue - Very Good
    elif restaurant['rating'] >= 4.0:
        color = "#f39c12"  # Orange - Good
    else:
        color = "#e74c3c"  # Red - Average
    
    # Create HTML card
    card_html = f"""
    <div style="background-color: {color}; border-radius: 12px; padding: 20px; margin: 15px 0; color: white;">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <div>
                <h3 style="margin: 0 0 8px 0;">{restaurant['name']}</h3>
                <p style="margin: 0 0 12px 0; opacity: 0.9;">
                    {restaurant['cuisine_type']} • {restaurant['price_level']} • {restaurant['dining_style']}
                </p>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 24px; font-weight: bold;">⭐ {restaurant['rating']}</div>
                <div style="font-size: 12px; opacity: 0.9;">{restaurant['review_count']} reviews</div>
            </div>
        </div>
        
        <p style="margin: 12px 0; font-style: italic;">{restaurant['description']}</p>
        
        <div style="margin: 15px 0; padding: 12px; background-color: rgba(255,255,255,0.1); border-radius: 8px;">
            <p style="margin: 0 0 8px 0;"><b>📍 Address:</b> {restaurant['address']}</p>
            <p style="margin: 0 0 8px 0;"><b>💵 Average Cost:</b> {restaurant['average_cost_per_person']}</p>
            <p style="margin: 0;"><b>🕐 Hours:</b> {restaurant['opening_hours']}</p>
        </div>
        
        <div style="margin: 12px 0;">
            <b>⭐ Signature Dishes:</b>
            <ul style="margin: 8px 0; padding-left: 20px;">
    """
    
    for dish in restaurant.get('best_dishes', []):
        card_html += f"<li>{dish['name']} ({dish['price']}) - ⭐ {dish['rating']}</li>"
    
    card_html += """
            </ul>
        </div>
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)
    
    # Display Google-style reviews
    st.markdown("#### 📝 Recent Google Reviews")
    
    for i, review in enumerate(restaurant.get('google_reviews', [])[:3]):
        review_html = f"""
        <div style="margin: 12px 0; padding: 12px; background-color: #f5f5f5; border-radius: 8px;">
            <div style="display: flex; justify-content: space-between;">
                <b>{review['reviewer_name']}</b>
                <span style="color: #666; font-size: 12px;">{review['date']}</span>
            </div>
            <div style="color: #ffc107; margin: 4px 0;">
        """
        
        # Draw star rating
        rating = review['rating']
        review_html += f"⭐ " * rating + f"☆ " * (5 - rating)
        review_html += f"""
            </div>
            <p style="margin: 8px 0 0 0; color: #333;">{review['review_text']}</p>
        </div>
        """
        
        st.markdown(review_html, unsafe_allow_html=True)

