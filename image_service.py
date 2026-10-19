"""
Image Service - Fetches beautiful travel photos from online sources
Supports Outscraper Google Images, Unsplash, Pixabay for destination photography

Keys are read from environment variables first, then fall back to the values below.
When a provider rejects the key (401/403) the provider is disabled for the rest of
the process, so the UI never waits on a dead API for every card.
"""

import os

import requests
from typing import List, Dict, Optional
import streamlit as st

from settings import get_secret


# =============================================================================
# External Image APIs Configuration
# =============================================================================

# Keys come from environment variables or .streamlit/secrets.toml (see settings.py).
UNSPLASH_ACCESS_KEY = get_secret("UNSPLASH_ACCESS_KEY", "YOUR_UNSPLASH_KEY")
PIXABAY_API_KEY = get_secret("PIXABAY_API_KEY", "YOUR_PIXABAY_KEY")
OUTSCRAPER_API_KEY = get_secret("OUTSCRAPER_API_KEY")

# Circuit breakers: flipped to True after the first rejected request.
_GOOGLE_IMAGES_DISABLED = False
_UNSPLASH_DISABLED = False


def _configured(value: str, placeholder: str = "YOUR_") -> bool:
    """True when a key looks real rather than a template placeholder."""
    return bool(value) and placeholder not in value


# =============================================================================
# Fetch Top 3 Google Images using Outscraper API (RECOMMENDED)
# =============================================================================

@st.cache_data(ttl=86400)  # Cache for 24 hours
def fetch_google_images_top3(query: str) -> List[Dict]:
    """
    Fetch top 3 images from Google Images using Outscraper API.
    Best for hotel names and attractions - gives high-quality results.
    
    Args:
        query: Search query (e.g., "Marriott Beijing", "Great Wall of China")
    
    Returns:
        List of top 3 image dicts with url, title, and source
    """
    global _GOOGLE_IMAGES_DISABLED
    try:
        if _GOOGLE_IMAGES_DISABLED or not _configured(OUTSCRAPER_API_KEY, "YOUR_API_KEY"):
            return []
        
        url = "https://api.outscraper.cloud/google-search-images"
        
        headers = {
            "X-API-KEY": OUTSCRAPER_API_KEY
        }
        
        params = {
            "query": query,
            "async": "false",  # Synchronous request for immediate results
            "perQuery": 3      # Top 3 results per query
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            images = []
            
            # Parse response from Outscraper
            if data.get('status') == 'Success' and data.get('data'):
                for item in data['data'][0][:3]:  # Get top 3 images
                    if item.get('original_image'):
                        images.append({
                            'source': 'Google Images',
                            'url': item.get('original_image', ''),
                            'title': item.get('title', query),
                            'source_domain': item.get('source', 'Google'),
                            'source_link': item.get('source_link', ''),
                            'attribution': f"From {item.get('source', 'Google Images')}"
                        })
            
            print(f"✅ Fetched {len(images)} Google images for '{query}'")
            return images
        else:
            if response.status_code in (401, 403):
                _GOOGLE_IMAGES_DISABLED = True
                print("⚠️ Outscraper key rejected - Google Image search disabled for this session")
            return []
            
    except Exception as e:
        print(f"❌ Error fetching Google images: {str(e)}")
        return []


# =============================================================================
# Fetch High-Quality Images from Unsplash
# =============================================================================

@st.cache_data(ttl=86400)  # Cache for 24 hours
def fetch_unsplash_images(query: str, per_page: int = 6) -> List[Dict]:
    """
    Fetch beautiful images from Unsplash.
    Free tier: 50 requests/hour.
    
    Args:
        query: Search query (e.g., "Bangkok temples", "Paris cafe")
        per_page: Number of images to return
    
    Returns:
        List of image dicts with url, photographer, and attribution
    """
    global _UNSPLASH_DISABLED
    try:
        if _UNSPLASH_DISABLED or not _configured(UNSPLASH_ACCESS_KEY):
            return []
        # Use public Unsplash API without key (limited to 50 requests/hour)
        url = "https://api.unsplash.com/search/photos"
        
        params = {
            "query": query,
            "per_page": per_page,
            "order_by": "relevant"
        }
        
        params["client_id"] = UNSPLASH_ACCESS_KEY
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            images = []
            
            for result in data.get('results', []):
                images.append({
                    'source': 'Unsplash',
                    'url': result['urls']['regular'],
                    'thumbnail': result['urls']['thumb'],
                    'title': result.get('description', result.get('alt_description', query)),
                    'photographer': result['user']['name'],
                    'photographer_url': result['user']['links']['html'],
                    'photo_url': result['links']['html'],
                    'attribution': f"Photo by {result['user']['name']} on Unsplash"
                })
            
            print(f"✅ Fetched {len(images)} images from Unsplash for '{query}'")
            return images
        else:
            if response.status_code in (401, 403):
                _UNSPLASH_DISABLED = True
                print("⚠️ Unsplash key rejected - Unsplash disabled for this session")
            return []
            
    except Exception as e:
        print(f"❌ Error fetching from Unsplash: {str(e)}")
        return []


# =============================================================================
# Fetch Images from Pixabay (Great for travel content)
# =============================================================================

@st.cache_data(ttl=86400)
def fetch_pixabay_images(query: str, per_page: int = 6) -> List[Dict]:
    """
    Fetch images from Pixabay.
    Free tier: 50 requests/day.
    
    Args:
        query: Search query
        per_page: Number of images
    
    Returns:
        List of image dicts
    """
    try:
        url = "https://pixabay.com/api/"
        
        params = {
            "q": query,
            "image_type": "photo",
            "per_page": per_page,
            "order": "popular",
            "safesearch": True,
            "min_width": 600,
            "min_height": 600
        }
        
        # Pixabay requires API key
        if PIXABAY_API_KEY == "YOUR_PIXABAY_KEY":
            print("⚠️ Pixabay API key not configured")
            return []
        
        params["key"] = PIXABAY_API_KEY
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            images = []
            
            for hit in data.get('hits', []):
                images.append({
                    'source': 'Pixabay',
                    'url': hit['largeImageURL'],
                    'thumbnail': hit['previewURL'],
                    'title': query,
                    'photographer': hit.get('user', 'Unknown'),
                    'photo_url': hit['pageURL'],
                    'attribution': f"Image from Pixabay"
                })
            
            print(f"✅ Fetched {len(images)} images from Pixabay for '{query}'")
            return images
        else:
            print(f"⚠️ Pixabay API error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error fetching from Pixabay: {str(e)}")
        return []


# =============================================================================
# Fetch Images (Now uses Outscraper Google Images - Pexels DEPRECATED)
# =============================================================================

@st.cache_data(ttl=86400)
def fetch_pexels_images(query: str, per_page: int = 6) -> List[Dict]:
    """
    Fetch images using Google Images via Outscraper API.
    ⚠️ Function renamed from 'fetch_pexels_images' but kept for backward compatibility.
    Primary source: Google Images via Outscraper (replaces old Pexels API)
    
    Args:
        query: Search query (e.g., "Marriott Hotel", "Great Wall")
        per_page: Number of images to return
    
    Returns:
        List of image dicts from Google Images with source attribution
    """
    try:
        # Use Google Images via Outscraper (primary source)
        google_images = fetch_google_images_top3(query)
        if google_images:
            return google_images[:per_page]
        
        # Fallback to Unsplash if Google Images is unavailable
        return fetch_unsplash_images(query, per_page)
            
    except Exception as e:
        print(f"❌ Error fetching images: {str(e)}")
        return fetch_unsplash_images(query, per_page)


# =============================================================================
# Combined Image Fetching with Fallback
# =============================================================================

def fetch_beautiful_images(location: str, category: str = "", per_page: int = 6) -> List[Dict]:
    """
    Fetch beautiful images for a travel destination.
    Tries multiple sources with fallback.
    
    Args:
        location: Destination name (e.g., "Bangkok", "Eiffel Tower")
        category: Image category (e.g., "temple", "street food", "market")
        per_page: Number of images per source
    
    Returns:
        Combined list of high-quality images from multiple sources
    """
    query = f"{location} {category}".strip()
    all_images = []
    
    # Try multiple sources
    print(f"\n🖼️ Fetching beautiful images for '{query}'...")
    
    # 1. Try Unsplash (best quality)
    unsplash_images = fetch_unsplash_images(query, per_page)
    all_images.extend(unsplash_images)
    
    # 2. Try Pexels (free, unlimited)
    pexels_images = fetch_pexels_images(query, per_page)
    all_images.extend(pexels_images)
    
    # 3. Try Pixabay (if configured)
    if PIXABAY_API_KEY != "YOUR_PIXABAY_KEY":
        pixabay_images = fetch_pixabay_images(query, per_page)
        all_images.extend(pixabay_images)
    
    # Remove duplicates by URL
    seen_urls = set()
    unique_images = []
    
    for img in all_images:
        if img['url'] not in seen_urls:
            seen_urls.add(img['url'])
            unique_images.append(img)
    
    print(f"✅ Total {len(unique_images)} unique images found")
    return unique_images[:12]  # Return up to 12 images


# =============================================================================
# Display Images in Streamlit
# =============================================================================

def display_image_gallery(images: List[Dict], title: str = ""):
    """Display images in a beautiful gallery grid"""
    import streamlit as st
    
    if not images:
        st.warning("No images found. Please try with a different search query.")
        return
    
    if title:
        st.subheader(f"🖼️ {title}")
    
    # Calculate grid columns
    cols = st.columns(min(3, len(images)))
    
    for idx, image in enumerate(images):
        col_idx = idx % 3
        
        if idx > 0 and idx % 3 == 0:
            cols = st.columns(min(3, len(images) - idx))
            col_idx = 0
        
        with cols[col_idx]:
            try:
                # Display image
                st.image(image['url'], use_container_width=True)
                
                # Display attribution
                st.caption(f"📸 {image['attribution']}")
                st.caption(f"Source: {image['source']}")
                
                # Provide link to full image
                st.markdown(f"[🔗 View original]({image['photo_url']})")
                
            except Exception as e:
                st.error(f"Error displaying image: {str(e)}")


def display_destination_images(destination: str):
    """Display a collection of beautiful images for a destination"""
    import streamlit as st
    
    st.subheader(f"📸 Beautiful Photos of {destination}")
    
    # Fetch images for main destination
    if st.button(f"🔍 Load Photos from {destination}", use_container_width=True, key=f"load_images_{destination}"):
        with st.spinner(f"Loading beautiful images of {destination}..."):
            # Try to fetch high-quality images
            images = fetch_beautiful_images(destination, "", per_page=6)
            
            if images:
                display_image_gallery(images, f"Explore {destination}")
                st.session_state[f"images_{destination}"] = images
            else:
                st.info("No images available. (Configure Unsplash/Pexels API keys for better results)")
    
    # Display cached images if available
    cache_key = f"images_{destination}"
    if cache_key in st.session_state:
        display_image_gallery(st.session_state[cache_key], f"Gallery: {destination}")


# =============================================================================
# Destination-Specific Image Categories
# =============================================================================

DESTINATION_IMAGE_CATEGORIES = {
    "Bangkok": ["temples", "markets", "street food", "nightlife", "river"],
    "Paris": ["Eiffel Tower", "cafes", "museums", "Seine", "architecture"],
    "Tokyo": ["temples", "streets", "food", "cherry blossoms", "gardens"],
    "Rome": ["Colosseum", "fountains", "restaurants", "history", "architecture"],
    "Barcelona": ["architecture", "beaches", "food", "neighborhoods", "culture"],
    "Venice": ["canals", "squares", "boats", "architecture", "sunset"],
    "Vienna": ["palaces", "music", "coffee culture", "architecture", "classical"],
    "Beijing": ["Great Wall", "Forbidden City", "temples", "street food", "markets"],
    "Havana": ["colonial", "cars", "culture", "music", "architecture"],
    "Bangkok": ["temples", "street food", "markets", "nightlife", "tuk-tuk"],
}


def display_category_images(destination: str):
    """Display images categorized by tourist attractions and experiences"""
    import streamlit as st
    
    categories = DESTINATION_IMAGE_CATEGORIES.get(destination, [destination])
    
    st.markdown(f"### 📸 Explore {destination} by Category")
    
    selected_category = st.selectbox(
        "Choose an experience:",
        categories,
        key=f"cat_select_{destination}"
    )
    
    if st.button("Load Photos", use_container_width=True, key=f"load_cat_images_{destination}"):
        with st.spinner(f"Loading photos of {selected_category} in {destination}..."):
            query = f"{destination} {selected_category}"
            images = fetch_beautiful_images(destination, selected_category, per_page=6)
            
            if images:
                display_image_gallery(images, f"{selected_category} in {destination}")
            else:
                st.info("No images available for this category. Try another search.")


# =============================================================================
# Get Images for Restaurant/Attractions
# =============================================================================

def fetch_restaurant_images(restaurant_name: str, cuisine: str = "") -> List[Dict]:
    """Fetch food/restaurant images"""
    query = f"{restaurant_name} {cuisine} restaurant"
    return fetch_beautiful_images(query, "food", per_page=3)


def fetch_attraction_images(attraction_name: str, location: str = "") -> List[Dict]:
    """Fetch images for tourist attractions"""
    query = f"{attraction_name} {location}"
    return fetch_beautiful_images(query, "", per_page=3)

