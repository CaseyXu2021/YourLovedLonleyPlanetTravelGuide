"""
World Map Interactive Country Selector
Shows available countries as green markers, others as gray
Hover shows book cover
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
from pathlib import Path
from typing import Optional, List
import base64

# Country coordinates (lat, lng for center of country)
COUNTRY_COORDS = {
    "Argentina": (-34.6037, -58.3816),
    "Austria": (48.2082, 16.3738),
    "Cambodia": (11.5564, 104.9910),
    "China": (39.9042, 116.4074),
    "Cuba": (23.1291, -82.3794),
    "Estonia, Latvia, Lithuania": (54.1161, 24.9522),
    "Europe": (50.0, 10.0),
    "Iran": (35.6892, 51.3890),
    "Italy": (41.9028, 12.4964),
    "Japan": (35.6762, 139.6503),
    "Malaysia, Singapore, Brunei": (1.3521, 103.8198),
    "Netherlands": (52.3676, 4.9041),
    "Poland": (52.2297, 21.0122),
    "Sicily": (37.5070, 13.5623),
    "Thailand": (13.7563, 100.5018),
    "West Africa": (6.4969, -1.0232),
    "Zambia, Mozambique, Malawi": (-15.3875, 28.3228),
}

def get_book_cover_base64(country_name: str, base_dir: Path) -> Optional[str]:
    """
    Get book cover image as base64 for hover display
    """
    cover_dir = base_dir / "cover_picture"
    
    # Try to find cover image
    if cover_dir.exists():
        for ext in [".png", ".jpg", ".jpeg"]:
            cover_file = cover_dir / f"{country_name}{ext}"
            if cover_file.exists():
                with open(cover_file, "rb") as f:
                    return base64.b64encode(f.read()).decode()
    
    return None


def create_world_map(available_countries: List[str], base_dir: Path) -> folium.Map:
    """
    Create interactive world map with available countries marked in green,
    others in gray
    """
    # Create base map centered on world
    m = folium.Map(
        location=[20, 0],
        zoom_start=2,
        tiles="OpenStreetMap"
    )
    
    # Add markers for all countries in our database
    for country_name, coords in COUNTRY_COORDS.items():
        if country_name in available_countries:
            # Green marker for available countries
            color = "green"
            prefix = "✅ "
        else:
            # Gray marker for unavailable
            color = "gray"
            prefix = "⚪ "
        
        # Create popup with country info
        popup_text = f"{prefix}{country_name}"
        
        folium.CircleMarker(
            location=coords,
            radius=8,
            popup=popup_text,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=2,
        ).add_to(m)
    
    return m


def render_map_selector(available_countries: List[str], base_dir: Path) -> Optional[str]:
    """
    Render the world map selector UI
    Returns: selected country name or None
    """
    st.markdown("## 🌍 Select Your Destination")
    st.markdown("Hover over markers to see details. Click a green marker to select.")
    
    # Create map
    m = create_world_map(available_countries, base_dir)
    
    # Display map and capture interaction
    map_data = st_folium(m, width=1400, height=600)
    
    selected_country = None
    
    # Check if user clicked on a marker
    if map_data and map_data.get("last_clicked"):
        clicked_coords = (map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"])
        
        # Find which country was clicked (with tolerance)
        for country_name, coords in COUNTRY_COORDS.items():
            lat_diff = abs(coords[0] - clicked_coords[0])
            lng_diff = abs(coords[1] - clicked_coords[1])
            
            if lat_diff < 5 and lng_diff < 5 and country_name in available_countries:
                selected_country = country_name
                st.session_state.selected_country = country_name
                break
    
    # Display book covers of available countries in a grid
    st.markdown("### 📚 Available Destinations")
    
    cols = st.columns(4)
    for idx, country in enumerate(sorted(available_countries)):
        with cols[idx % 4]:
            cover_image = get_book_cover_base64(country, base_dir)
            
            if cover_image:
                st.image(
                    f'<img src="data:image/png;base64,{cover_image}" width="150"/>',
                    use_column_width=True
                )
            else:
                st.write(f"📖 {country}")
            
            if st.button(f"Select {country}", key=f"btn_{country}"):
                selected_country = country
                st.session_state.selected_country = country
                st.rerun()
    
    return selected_country
