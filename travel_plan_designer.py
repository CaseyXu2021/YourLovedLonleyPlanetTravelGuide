import os
"""
Travel Plan Designer - Generate beautiful Word documents
Create comprehensive travel plans with formatting
"""

import streamlit as st
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import json
from openai import AzureOpenAI

# Configuration
from settings import AZURE_API_KEY  # noqa: E402
AZURE_ENDPOINT = "https://hkust.azure-api.net"
AZURE_DEPLOYMENT_NAME = "gpt-4o-mini"


def shade_cell(cell, color):
    """Shade a table cell with a color"""
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:fill'), color)
    cell._element.get_or_add_tcPr().append(shading_elm)


def create_travel_plan_document(
    country: str,
    city: str,
    duration_days: int,
    attractions: List[Dict],
    weather: Optional[List[Dict]] = None,
    custom_notes: str = ""
) -> Document:
    """
    Create a beautiful Word document for travel plan
    """
    
    doc = Document()
    
    # Set up styles
    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(11)
    
    # ========== TITLE PAGE ==========
    title = doc.add_heading('🌍 Your Travel Plan', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_format = title.runs[0]
    title_format.font.size = Pt(28)
    title_format.font.bold = True
    title_format.font.color.rgb = RGBColor(0, 102, 204)
    
    # Subtitle
    subtitle = doc.add_paragraph(f'{city}, {country}')
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_format = subtitle.runs[0]
    subtitle_format.font.size = Pt(20)
    subtitle_format.font.color.rgb = RGBColor(100, 100, 100)
    
    # Plan date
    date_para = doc.add_paragraph(f'Generated: {datetime.now().strftime("%B %d, %Y")}')
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph()  # Spacer
    
    # ========== QUICK FACTS ==========
    doc.add_heading('📋 Quick Facts', level=1)
    
    facts_table = doc.add_table(rows=4, cols=2)
    facts_table.style = 'Light Grid Accent 1'
    
    facts = [
        ("Destination", f"{city}, {country}"),
        ("Duration", f"{duration_days} days"),
        ("Plan Date", datetime.now().strftime("%B %d, %Y")),
        ("Packed With", f"{len(attractions)} attractions")
    ]
    
    for idx, (key, value) in enumerate(facts):
        facts_table.rows[idx].cells[0].text = key
        facts_table.rows[idx].cells[1].text = str(value)
        shade_cell(facts_table.rows[idx].cells[0], 'ADD8E6')  # Light blue
    
    doc.add_paragraph()  # Spacer
    
    # ========== WEATHER FORECAST ==========
    if weather:
        doc.add_heading('🌤️ Weather Forecast', level=1)
        
        weather_table = doc.add_table(rows=len(weather) + 1, cols=3)
        weather_table.style = 'Light Grid Accent 1'
        
        # Header
        header_cells = weather_table.rows[0].cells
        header_cells[0].text = 'Date'
        header_cells[1].text = 'Max Temp'
        header_cells[2].text = 'Min Temp'
        
        for idx, cell in enumerate(header_cells):
            shade_cell(cell, 'FFD700')  # Gold
        
        # Data
        for idx, forecast in enumerate(weather, 1):
            cells = weather_table.rows[idx].cells
            cells[0].text = forecast.get('date', '')
            cells[1].text = f"{int(forecast.get('temp_max', 0))}°C"
            cells[2].text = f"{int(forecast.get('temp_min', 0))}°C"
        
        doc.add_paragraph()  # Spacer
    
    # ========== ITINERARY ==========
    doc.add_heading('📅 Day-by-Day Itinerary', level=1)
    
    # Generate itinerary using Azure OpenAI
    try:
        client = AzureOpenAI(
            api_key=AZURE_API_KEY,
            api_version="2024-10-21",
            azure_endpoint=AZURE_ENDPOINT,
        )
        
        attractions_text = "\n".join([
            f"- {attr.get('name', 'Unknown')}: {attr.get('description', '')}"
            for attr in attractions[:10]
        ])
        
        prompt = f"""Create a {duration_days}-day itinerary for {city}, {country}.
Include:
- Morning activities
- Lunch recommendations (based on local cuisine)
- Afternoon activities
- Evening activities
- Practical tips

Selected attractions to include:
{attractions_text}

Format as a detailed, engaging travel guide."""
        
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are a professional travel guide writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        itinerary_text = response.choices[0].message.content
        
        # Split into days and add to document
        days = itinerary_text.split('\n\n')
        for day_idx, day_content in enumerate(days[:duration_days], 1):
            day_heading = doc.add_heading(f'Day {day_idx}', level=2)
            day_heading_format = day_heading.runs[0]
            day_heading_format.font.color.rgb = RGBColor(204, 0, 0)
            
            doc.add_paragraph(day_content)
    
    except Exception as e:
        doc.add_paragraph(f"Error generating itinerary: {e}")
    
    doc.add_paragraph()  # Spacer
    
    # ========== ATTRACTIONS ==========
    doc.add_heading('⭐ Selected Attractions', level=1)
    
    for idx, attr in enumerate(attractions[:20], 1):
        # Attraction entry
        attr_para = doc.add_paragraph()
        attr_run = attr_para.add_run(f"{idx}. {attr.get('name', 'Unknown')}")
        attr_run.bold = True
        attr_run.font.size = Pt(12)
        
        # Rating and type
        details = f"⭐ {attr.get('rating', 'N/A')} | {attr.get('category', 'Attraction')}"
        doc.add_paragraph(details, style='List Bullet')
        
        # Description
        if attr.get('description'):
            doc.add_paragraph(attr['description'], style='List Bullet')
    
    doc.add_paragraph()  # Spacer
    
    # ========== PRACTICAL INFORMATION ==========
    doc.add_heading('ℹ️ Practical Information', level=1)
    
    practical_info = f"""
🏨 Accommodation: 
   - Book hotels in advance during peak season
   - Consider location near public transportation
   
🚗 Transportation:
   - Public transport is recommended
   - Get a local SIM card or international plan for navigation
   
💰 Money Matters:
   - Check exchange rates before traveling
   - Notify your bank of travel dates
   - Keep some cash on hand
   
🛡️ Safety:
   - Register with your embassy
   - Keep copies of important documents
   - Follow local travel advisories
   
📱 Useful Apps:
   - Google Maps for navigation
   - Google Translate for language help
   - Local public transport apps
"""
    
    doc.add_paragraph(practical_info)
    
    # ========== CUSTOM NOTES ==========
    if custom_notes:
        doc.add_heading('📝 Additional Notes', level=1)
        doc.add_paragraph(custom_notes)
    
    # ========== FOOTER ==========
    doc.add_paragraph()
    footer = doc.add_paragraph('✨ Have an amazing trip! 🌍')
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_format = footer.runs[0]
    footer_format.font.italic = True
    footer_format.font.size = Pt(12)
    footer_format.font.color.rgb = RGBColor(100, 100, 100)
    
    return doc


def render_plan_creator(
    country: str,
    city: str,
    attractions: List[Dict],
    weather: Optional[List[Dict]] = None
) -> Optional[Document]:
    """
    Render UI for creating travel plan
    Returns: Document object or None
    """
    
    st.markdown(f"## ✈️ Create Your {city} Travel Plan")
    
    # Input fields
    col1, col2 = st.columns(2)
    
    with col1:
        duration = st.slider(
            "🗓️ Trip Duration (days)",
            min_value=1,
            max_value=30,
            value=7,
            key="plan_duration"
        )
    
    with col2:
        style = st.selectbox(
            "🎨 Plan Style",
            ["Adventurous", "Relaxed", "Cultural", "Luxury"],
            key="plan_style"
        )
    
    # Custom notes
    custom_notes = st.text_area(
        "📝 Any specific requirements or preferences?",
        height=100,
        placeholder="E.g., vegetarian options, accessibility needs, budget constraints...",
        key="plan_notes"
    )
    
    # Generate button
    if st.button("📄 Generate Travel Plan (Word)", type="primary", use_container_width=True):
        
        with st.spinner("✨ Generating your beautiful travel plan..."):
            doc = create_travel_plan_document(
                country=country,
                city=city,
                duration_days=duration,
                attractions=attractions,
                weather=weather,
                custom_notes=custom_notes
            )
        
        # Save and provide download
        output_dir = Path(__file__).resolve().parent / "generated_plans"
        output_dir.mkdir(exist_ok=True)
        
        filename = f"TravelPlan_{city}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        filepath = output_dir / filename
        
        doc.save(str(filepath))
        
        st.success(f"✅ Travel plan created: {filename}")
        
        # Provide download
        with open(filepath, 'rb') as f:
            st.download_button(
                label="📥 Download Travel Plan (Word)",
                data=f.read(),
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        
        return doc
    
    return None


def render_plan_viewer():
    """
    View previously generated plans
    """
    st.markdown("## 📚 Your Travel Plans")
    
    plans_dir = Path(__file__).resolve().parent / "generated_plans"
    
    if not plans_dir.exists() or not list(plans_dir.glob("*.docx")):
        st.info("No travel plans generated yet. Create one to get started!")
        return
    
    # List all plans
    plans = sorted(plans_dir.glob("*.docx"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    for plan_file in plans:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.write(f"📄 {plan_file.name}")
        
        with col2:
            with open(plan_file, 'rb') as f:
                st.download_button(
                    label="⬇️",
                    data=f.read(),
                    file_name=plan_file.name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"dl_{plan_file.name}"
                )
