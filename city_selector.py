import os
"""
City Selector with Weather Forecast and Attractions
Show available cities, 7-day weather, and attractions
"""

import streamlit as st
from typing import List, Dict, Optional
import json
from datetime import datetime, timedelta
from openai import AzureOpenAI
import requests

# Configuration
from settings import AZURE_API_KEY  # noqa: E402
AZURE_ENDPOINT = "https://hkust.azure-api.net"
AZURE_DEPLOYMENT_NAME = "gpt-4o-mini"

# Pexels API for images
PEXELS_API_KEY = ""  # Will use old method if not set


def get_top_cities_for_country(country_name: str) -> Optional[List[Dict]]:
    """
    Use Azure OpenAI to get top cities for a country
    Returns list of cities with details
    """
    try:
        client = AzureOpenAI(
            api_key=AZURE_API_KEY,
            api_version="2024-10-21",
            azure_endpoint=AZURE_ENDPOINT,
        )
        
        prompt = f"""Generate top 5 tourist cities in {country_name}.
For each city, provide:
- name: City name
- description: Brief 1-line description
- attractions_count: Number of major attractions (estimate)
- best_for: What the city is famous for

Return as JSON array only."""
        
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are a travel expert. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Parse response
        response_text = response.choices[0].message.content
        
        # Extract JSON from response
        try:
            cities = json.loads(response_text)
            return cities if isinstance(cities, list) else None
        except json.JSONDecodeError:
            # Try to extract JSON from text
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                try:
                    cities = json.loads(json_match.group())
                    return cities if isinstance(cities, list) else None
                except:
                    pass
        
        return None
    
    except Exception as e:
        st.error(f"Error fetching cities: {e}")
        return None


def get_weather_forecast(city_name: str, country_name: str) -> Optional[List[Dict]]:
    """
    Get 7-day weather forecast for a city using Open-Meteo API
    Returns list of daily forecasts
    """
    try:
        import requests
        from geopy.geocoders import Nominatim
        
        # Geocode city
        geolocator = Nominatim(user_agent="travel_planner")
        location = geolocator.geocode(f"{city_name}, {country_name}", timeout=10)
        
        if not location:
            return None
        
        # Get weather from Open-Meteo
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
            "timezone": "auto"
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "daily" not in data:
            return None
        
        daily = data["daily"]
        forecasts = []
        
        for i in range(min(7, len(daily["time"]))):
            forecasts.append({
                "date": daily["time"][i],
                "temp_max": daily["temperature_2m_max"][i],
                "temp_min": daily["temperature_2m_min"][i],
                "precipitation": daily["precipitation_sum"][i],
                "weather_code": daily["weather_code"][i]
            })
        
        return forecasts
    
    except Exception as e:
        st.warning(f"Could not fetch weather: {e}")
        return None


def get_attractions_for_city(city_name: str, country_name: str) -> Optional[Dict]:
    """
    Get attractions for a city using Azure OpenAI
    Returns dict with top, medium, and worst attractions
    """
    try:
        client = AzureOpenAI(
            api_key=AZURE_API_KEY,
            api_version="2024-10-21",
            azure_endpoint=AZURE_ENDPOINT,
        )
        
        prompt = f"""Generate attractions database for {city_name}, {country_name}.
For EACH attraction, provide:
{{
  "name": "Name",
  "rating": 4.5,
  "reviews": 1000,
  "type": "top|medium|worst",
  "category": "culture|nature|food|museum|temple|park|beach",
  "description": "1-sentence description"
}}

Return exactly 3 sections:
TOP 10 (best rated)
TOP 10 RESTAURANTS (food focused)
TOP 10 HOTELS (accommodation)
WORST 10 (lowest rated)

Return as valid JSON only."""
        
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are a travel expert. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        response_text = response.choices[0].message.content
        
        # Extract and parse JSON
        try:
            attractions = json.loads(response_text)
            return attractions
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    attractions = json.loads(json_match.group())
                    return attractions
                except:
                    pass
        
        return None
    
    except Exception as e:
        st.error(f"Error fetching attractions: {e}")
        return None


def render_weather_forecast(forecasts: List[Dict]):
    """Render 7-day weather forecast as horizontal cards"""
    if not forecasts:
        return
    
    st.markdown("### 🌤️ 7-Day Weather Forecast")
    
    cols = st.columns(7)
    for idx, forecast in enumerate(forecasts):
        with cols[idx]:
            date = forecast["date"]
            temp_max = forecast["temp_max"]
            temp_min = forecast["temp_min"]
            
            st.metric(
                label=date,
                value=f"{int(temp_max)}°C",
                delta=f"Low: {int(temp_min)}°C"
            )


def render_attractions_selector(attractions: Dict) -> List[str]:
    """
    Render attractions with checkboxes for selection
    Returns list of selected attraction names
    """
    selected_attractions = []
    
    st.markdown("### ⭐ Select Attractions & Venues")
    
    # Create tabs for different categories
    tabs = st.tabs(["Top Attractions", "Hotels", "Restaurants", "Worst Rated"])
    
    with tabs[0]:  # Top Attractions
        if attractions.get("top"):
            for attr in attractions["top"][:10]:
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.checkbox(
                        f"☑️ {attr.get('name', 'Unknown')}",
                        key=f"attr_{attr.get('name', 'unknown')}"
                    ):
                        selected_attractions.append(attr)
                with col2:
                    st.write(
                        f"⭐ {attr.get('rating', 'N/A')} | "
                        f"{attr.get('reviews', 0)} reviews"
                    )
    
    with tabs[1]:  # Hotels
        if attractions.get("hotels"):
            for hotel in attractions["hotels"][:10]:
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.checkbox(
                        f"🏨 {hotel.get('name', 'Unknown')}",
                        key=f"hotel_{hotel.get('name', 'unknown')}"
                    ):
                        selected_attractions.append(hotel)
                with col2:
                    st.write(
                        f"⭐ {hotel.get('rating', 'N/A')} | "
                        f"{hotel.get('reviews', 0)} reviews"
                    )
    
    with tabs[2]:  # Restaurants
        if attractions.get("restaurants"):
            for rest in attractions["restaurants"][:10]:
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.checkbox(
                        f"🍽️ {rest.get('name', 'Unknown')}",
                        key=f"rest_{rest.get('name', 'unknown')}"
                    ):
                        selected_attractions.append(rest)
                with col2:
                    st.write(
                        f"⭐ {rest.get('rating', 'N/A')} | "
                        f"{rest.get('reviews', 0)} reviews"
                    )
    
    with tabs[3]:  # Worst Rated
        if attractions.get("worst"):
            for attr in attractions["worst"][:10]:
                st.warning(
                    f"⚠️ {attr.get('name', 'Unknown')} - "
                    f"Rating: {attr.get('rating', 'N/A')}"
                )
    
    return selected_attractions


def render_city_selector(country_name: str) -> Optional[Dict]:
    """
    Main render function for city selection page
    Returns: {"city": city_name, "attractions": [...], "weather": [...]}
    """
    st.markdown(f"## 🏙️ Select Cities in {country_name}")
    
    # Get cities for country
    with st.spinner(f"Finding top cities in {country_name}..."):
        cities = get_top_cities_for_country(country_name)
    
    if not cities:
        st.error("Could not fetch cities for this country")
        return None
    
    # Display cities in columns
    st.markdown("### 🌆 Top Cities")
    cols = st.columns(len(cities))
    
    selected_city = None
    for idx, city in enumerate(cities):
        with cols[idx]:
            st.markdown(f"**{city.get('name', 'Unknown')}**")
            st.write(city.get('description', ''))
            st.caption(f"🎯 {city.get('best_for', '')}")
            
            if st.button(f"Select {city.get('name')}", key=f"city_{city.get('name')}"):
                selected_city = city.get('name')
                st.session_state.selected_city = selected_city
    
    if not selected_city and "selected_city" in st.session_state:
        selected_city = st.session_state.selected_city
    
    if selected_city:
        st.divider()
        
        # Get weather for selected city
        weather = get_weather_forecast(selected_city, country_name)
        if weather:
            render_weather_forecast(weather)
        
        st.divider()
        
        # Get attractions for selected city
        with st.spinner(f"Finding attractions in {selected_city}..."):
            attractions = get_attractions_for_city(selected_city, country_name)
        
        if attractions:
            selected_attrs = render_attractions_selector(attractions)
            
            # Make travel plan button
            if st.button(
                "▶️ Let's Make Travel Plan",
                type="primary",
                use_container_width=True,
                key="make_plan_btn"
            ):
                st.session_state.selected_attractions = selected_attrs
                st.session_state.current_page = "create_plan"
                st.rerun()
        
        return {
            "city": selected_city,
            "weather": weather,
            "attractions": attractions
        }
    
    return None
