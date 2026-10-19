"""
地图选择器 - 使用folium创建交互式世界地图选择旅游目的地
支持地图点击选择和下拉框联动
"""

import folium
import streamlit as st
from streamlit_folium import st_folium
from typing import List, Optional

# Country coordinates (capital cities)
COUNTRY_COORDINATES = {
    "Austria": (48.2082, 16.3738, "Vienna"),
    "Cambodia": (11.5564, 104.9282, "Phnom Penh"),
    "China": (39.9042, 116.4074, "Beijing"),
    "Cuba": (23.1291, -82.3794, "Havana"),
    "Estonia": (59.4370, 24.7536, "Tallinn"),
    "Estonia, Latvia, Lithuania": (55.1694, 24.8383, "Vilnius"),
    "Europe": (50.1109, 8.6821, "Frankfurt"),
    "Iran": (35.6892, 51.3889, "Tehran"),
    "Italy": (41.9028, 12.4964, "Rome"),
    "Malaysia": (3.1390, 101.6869, "Kuala Lumpur"),
    "Malaysia, Singapore, Brunei": (1.3521, 103.8198, "Singapore"),
    "Poland": (52.2297, 21.0122, "Warsaw"),
    "Thailand": (13.7563, 100.5018, "Bangkok"),
    "West Africa": (6.8276, -5.2893, "Accra"),
    "Zambia": (-10.8355, 34.5199, "Lusaka"),
    "Zambia, Mozambique, Malawi": (-15.3875, 28.2882, "Lilongwe"),
}


def create_country_map(available_countries: List[str], selected_country: Optional[str] = None) -> folium.Map:
    """
    创建交互式世界地图
    绿色标记 = 有RAG库的国家
    灰色标记 = 其他国家
    蓝色标记 = 当前选中的国家
    """
    # 创建基础地图
    m = folium.Map(
        location=[20, 0],
        zoom_start=2,
        tiles="OpenStreetMap",
        prefer_canvas=True
    )
    
    # 遍历所有国家
    for country, (lat, lon, city_name) in COUNTRY_COORDINATES.items():
        has_kb = country in available_countries
        
        # 根据选择状态设置颜色
        if country == selected_country:
            color = "blue"
            icon_symbol = "star"
        else:
            color = "green" if has_kb else "gray"
            icon_symbol = "check" if has_kb else "ban"
        
        icon_color = "white" if (country == selected_country or has_kb) else "black"
        
        popup_html = f"""
        <div style="font-family: Arial; width: 200px;">
            <h4 style="margin: 0 0 8px 0; color: #2c3e50;">{country}</h4>
            <div style="font-size: 12px; color: #555;">
                <p style="margin: 4px 0;"><b>Capital:</b> {city_name}</p>
                <p style="margin: 4px 0; color: {'#27ae60' if has_kb else '#e74c3c'};"><b>Status:</b> {'✅ Available' if has_kb else '❌ Not Available'}</p>
            </div>
        </div>
        """
        
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"Click to select {country}",
            icon=folium.Icon(
                color=color,
                icon=icon_symbol,
                prefix="fa",
                icon_color=icon_color,
                prefix_size=20
            )
        ).add_to(m)
    
    return m


def render_interactive_map(available_countries: List[str], current_selection: Optional[str] = None) -> dict:
    """
    渲染交互式地图选择器 - 支持地图点击和联动
    返回地图交互数据
    """
    st.subheader("🗺️ Interactive World Map - Select Your Destination")
    
    col_legend, col_info = st.columns([2, 3])
    with col_legend:
        st.markdown("""
        **🗺️ Legend:**
        - 🟢 **Green Marker**: Available destination
        - ⚫ **Gray Marker**: Not available yet
        - 🔵 **Blue Marker**: Currently selected
        """)
    
    with col_info:
        st.info("💡 Click on any green marker to select a destination, then press the **Confirm Selection** button to update!")
    
    # Create map with current selection
    m = create_country_map(available_countries, current_selection)
    
    # Render map and capture interaction
    map_data = st_folium(m, width=1000, height=450, key="interactive_map")
    
    return map_data


def get_selected_country_from_map(map_data: dict, available_countries: List[str]) -> Optional[str]:
    """
    从地图交互数据中提取选中的国家
    返回国家名称或 None
    """
    if not map_data or not map_data.get("last_clicked"):
        return None
    
    # 获取最后点击的坐标
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    
    # 找到最近的国家
    min_distance = float("inf")
    closest_country = None
    
    for country, (country_lat, country_lon, _) in COUNTRY_COORDINATES.items():
        if country not in available_countries:
            continue
        
        # 计算简单欧几里得距离
        distance = ((lat - country_lat) ** 2 + (lon - country_lon) ** 2) ** 0.5
        
        if distance < min_distance:
            min_distance = distance
            closest_country = country
    
    # 只有在距离足够近时才认为是有效的选择（避免误点）
    if min_distance < 15 and closest_country:
        return closest_country
    
    return None

