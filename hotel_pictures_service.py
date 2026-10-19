"""
Hotel Pictures Service - Fetches photos for hotels from Google Images
Uses Outscraper API to get beautiful hotel and accommodation photos from Google Images
"""

import os

import requests
from typing import List, Dict, Optional
import streamlit as st

from settings import get_secret


# =============================================================================
# Outscraper Google Images API Configuration
# =============================================================================

OUTSCRAPER_API_KEY = get_secret("OUTSCRAPER_API_KEY")

# Circuit breaker: set after the first rejected request so we stop retrying.
_OUTSCRAPER_DISABLED = False


# =============================================================================
# Fetch Hotel Photos from Google Images (via Outscraper)
# =============================================================================

@st.cache_data(ttl=86400)  # Cache for 24 hours
def fetch_hotel_images(hotel_name: str, city: str = "", per_page: int = 3) -> List[Dict]:
    """
    Fetch beautiful hotel/accommodation images from Google Images using Outscraper API.
    
    Args:
        hotel_name: Name of the hotel
        city: City where the hotel is located
        per_page: Number of images to return (default: 3 for top 3 images)
    
    Returns:
        List of image dicts with url, title, and source
    """
    try:
        global _OUTSCRAPER_DISABLED
        if _OUTSCRAPER_DISABLED or not OUTSCRAPER_API_KEY or "YOUR_" in OUTSCRAPER_API_KEY:
            return get_generic_hotel_images(city)
        
        # Construct search query with hotel name and city
        search_query = f"{hotel_name} {city}" if city else hotel_name
        
        url = "https://api.outscraper.cloud/google-search-images"
        
        headers = {
            "X-API-KEY": OUTSCRAPER_API_KEY
        }
        
        params = {
            "query": search_query,
            "async": "false",  # Synchronous request
            "perQuery": per_page  # Top N images per query
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            images = []
            
            # Parse response from Outscraper
            if data.get('status') == 'Success' and data.get('data'):
                results = data['data'][0][:per_page]  # Get top N images
                
                for item in results:
                    if item.get('original_image'):
                        images.append({
                            'source': 'Google Images',
                            'url': item.get('original_image', ''),
                            'title': item.get('title', hotel_name),
                            'source_domain': item.get('source', 'Google'),
                            'source_link': item.get('source_link', ''),
                            'attribution': f"Hotel image from {item.get('source', 'Google Images')}"
                        })
            
            print(f"✅ Fetched {len(images)} hotel images for '{hotel_name}' in {city}")
            return images if images else get_generic_hotel_images(city)
        else:
            if response.status_code in (401, 403):
                _OUTSCRAPER_DISABLED = True
                print("⚠️ Outscraper key rejected - hotel photos fall back to generic images")
            return get_generic_hotel_images(city)
            
    except Exception as e:
        print(f"❌ Error fetching hotel images: {str(e)}")
        return get_generic_hotel_images(city)


# =============================================================================
# Generic Hotel Images (Fallback)
# =============================================================================

def get_generic_hotel_images(city: str = "") -> List[Dict]:
    """
    Return generic hotel images when API is not available.
    These are placeholder descriptions that can be displayed.
    """
    generic_images = [
        {
            'source': 'Generic',
            'url': 'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=500',
            'thumbnail': 'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=200',
            'photographer': 'Hotel Photography',
            'photographer_url': '',
            'photo_url': '',
            'attribution': 'Luxury Hotel Room'
        },
        {
            'source': 'Generic',
            'url': 'https://images.unsplash.com/photo-1572535967248-cb4f3c5d0f1b?w=500',
            'thumbnail': 'https://images.unsplash.com/photo-1572535967248-cb4f3c5d0f1b?w=200',
            'photographer': 'Hotel Photography',
            'photographer_url': '',
            'photo_url': '',
            'attribution': 'Hotel Lobby & Reception'
        },
        {
            'source': 'Generic',
            'url': 'https://images.unsplash.com/photo-1582719471384-894fbb16e074?w=500',
            'thumbnail': 'https://images.unsplash.com/photo-1582719471384-894fbb16e074?w=200',
            'photographer': 'Hotel Photography',
            'photographer_url': '',
            'photo_url': '',
            'attribution': 'Hotel Amenities'
        }
    ]
    
    return generic_images[:3]


# =============================================================================
# Display Hotel Images
# =============================================================================

def display_hotel_photos(hotel_data: Dict):
    """Display hotel photos in a beautiful gallery format"""
    import streamlit as st
    
    hotel_name = hotel_data.get('name', 'Hotel')
    
    # Fetch images for this hotel
    images = fetch_hotel_images(hotel_name, hotel_data.get('city', ''), per_page=4)
    
    if images:
        st.subheader(f"🏨 {hotel_name} Photos")
        
        cols = st.columns(min(2, len(images)))
        
        for idx, image in enumerate(images):
            col_idx = idx % 2
            
            if idx > 0 and idx % 2 == 0:
                cols = st.columns(min(2, len(images) - idx))
                col_idx = 0
            
            with cols[col_idx]:
                try:
                    st.image(image['url'], use_container_width=True)
                    st.caption(f"📸 {image['attribution']}")
                except Exception as e:
                    st.warning(f"Could not load image")
