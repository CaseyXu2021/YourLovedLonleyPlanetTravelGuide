"""
Lonely Planet Intelligent Travel Guide_Group7
Semantic Search + LLM-powered travel recommendations.
Version 2.0
Group 7:
**Casey: Code Demo
**Jasper: Code Revision
**Maxine: Demo Vedio, Proposal Picture
**Paew: Streamlit UI, Proposal

"""

import streamlit as st
import numpy as np
import pickle
import os
import base64
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from openai import AzureOpenAI
from image_carousel import image_carousel
from embedding_backend import embed_query, get_embedder, loaded_engine_name
from image_service import fetch_beautiful_images, fetch_pexels_images
from hotels_service import generate_hotels_for_city
from hotel_pictures_service import fetch_hotel_images
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email import encoders
    HAS_EMAIL = True
except ImportError:
    HAS_EMAIL = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import folium
    from streamlit_folium import st_folium
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False

try:
    from geopy.geocoders import Nominatim
    HAS_GEOPY = True
except ImportError:
    HAS_GEOPY = False


# =============================================================================
# Page configuration and path setup
# =============================================================================

st.set_page_config(
    page_title="🌍 You Loved Lonely Planet: Intelligent Travel Guide",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

_BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = _BASE_DIR / "knowledge_bases"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Azure OpenAI configuration
# =============================================================================

from settings import (  # noqa: E402  (secrets loaded from env / secrets.toml)
    AZURE_API_KEY,
    AZURE_API_VERSION,
    AZURE_DEPLOYMENT_NAME,
    AZURE_ENDPOINT,
)


# =============================================================================
# Embedding model loading (lazy, onnxruntime - no PyTorch needed)
# =============================================================================

def get_embedding_model():
    """Return the shared MiniLM embedder (loaded once per process)."""
    return get_embedder()


# =============================================================================
# Display top banner with background image
# =============================================================================

def display_top_banner(title: str = "Your Loved Lonely Planet Travel Guide"):
    """Display title with background image banner."""
    banner_image_path = next(
        (
            p
            for p in (
                _BASE_DIR / "web top background picture.jpg",
                _BASE_DIR / "web top background picture.png",
            )
            if p.exists()
        ),
        None,
    )

    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.title(title)
        if banner_image_path is not None:
            st.image(str(banner_image_path), use_container_width=True)
        st.divider()


def cover_image_path(cover_dir: Path, country: str) -> Optional[Path]:
    """Resolve a destination cover whatever its extension (.png/.jpg/.jpeg)."""
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        candidate = cover_dir / f"{country}{ext}"
        if candidate.exists():
            return candidate
    return None


# =============================================================================
# Knowledge base and semantic search
# =============================================================================

@st.cache_resource(show_spinner=False)
def load_knowledge_base(country_name: str) -> Optional[Dict]:
    """Load and cache the knowledge base pickle, with L2-normalised embeddings.

    Two chunk schemas exist in `knowledge_bases/`:
      * {text, page, chunk_id[, country]}          - page-aware export
      * {text, start_char, end_char}               - character-offset export
    The second kind gets an estimated page number so citations work everywhere.
    """
    file_path = DATA_DIR / f"{country_name}.pkl"
    if not file_path.exists():
        return None
    with open(file_path, "rb") as f:
        kb = pickle.load(f)

    chunks = kb.get("chunks", [])
    chars_per_page = 1800
    max_page = 0
    for i, chunk in enumerate(chunks):
        if "page" not in chunk or chunk["page"] in (None, ""):
            start = chunk.get("start_char")
            chunk["page"] = int(start // chars_per_page) + 1 if isinstance(start, (int, float)) else i + 1
            chunk["page_estimated"] = True
        try:
            max_page = max(max_page, int(chunk["page"]))
        except (TypeError, ValueError):
            chunk["page"] = i + 1
        chunk.setdefault("chunk_id", f"{country_name}_{i}")
        chunk.setdefault("country", country_name)

    kb["total_pages"] = kb.get("total_pages") or max_page
    embeddings = np.asarray(kb["embeddings"], dtype=np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    kb["embeddings"] = embeddings / np.clip(norms, 1e-12, None)
    return kb


def semantic_search(
    query: str,
    country_name: str,
    top_k: int = 5,
) -> Tuple[List[Dict], np.ndarray]:
    """Retrieve top-k most relevant text chunks via cosine similarity."""
    kb = load_knowledge_base(country_name)
    if not kb or not kb.get("chunks"):
        return [], np.array([])

    query_vec = embed_query(query, get_embedding_model())
    scores = kb["embeddings"] @ query_vec

    top_k = min(top_k, len(scores))
    top_idx = np.argsort(-scores)[:top_k]

    results = []
    for idx in top_idx:
        chunk = dict(kb["chunks"][int(idx)])
        chunk["similarity"] = float(scores[int(idx)])
        chunk["relevance_pct"] = f"{scores[int(idx)] * 100:.1f}%"
        results.append(chunk)

    return results, scores[top_idx]


# =============================================================================
# Keyword extraction from retrieved texts
# =============================================================================

def extract_keywords(texts: List[str], top_n: int = 5) -> List[str]:
    """Extract top-n frequent keywords after filtering stop words."""
    combined_text = " ".join(texts).lower()

    stop_words = {
        "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
        "is", "are", "was", "were", "be", "been", "have", "has", "had",
        "a", "an", "this", "that", "these", "those", "it", "its", "page",
        "lonely", "planet", "guide", "book", "edition", "chapter", "visit",
        "located", "km", "hours", "day", "days", "week", "weeks", "month",
    }

    words = re.findall(r"\b[a-zA-Z\u4e00-\u9fa5]{3,}\b", combined_text)
    word_freq = {}
    for word in words:
        if word not in stop_words and not word.isdigit():
            word_freq[word] = word_freq.get(word, 0) + 1

    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:top_n]]


# =============================================================================
# RAG prompt construction for LLM
# =============================================================================

def build_rag_prompt(query: str, contexts: List[Dict]) -> str:
    """Build the RAG prompt with reference chunks and answer format instructions."""
    context_text = "\n\n".join(
        [
            f"[Source: Page {c['page']}, Relevance: {c['relevance_pct']}]\n{c['text'][:1000]}"
            for c in contexts
        ]
    )

    prompt = f"""Based on the following excerpts from Lonely Planet travel guides, answer the user's question.

[Reference Document Content]
{context_text}

[User Question]
{query}

[Answer Requirements]
1. First list 3-5 core keywords (Key Highlights)
2. Then provide detailed travel advice with specific place names and practical suggestions, sue bulletpoint with emoji for better readability
3. Mark information sources with page numbers (Page X), use yellow to high the page number
4. If document lacks relevant information, state "Unable to determine based on current information"
5. Maintain a friendly and professional travel advisor tone

Please output in the following format:

**Keywords**: Keyword1, Keyword2, Keyword3...

**Detailed Suggestions**:
(Detailed content with page references like [Page 23])

**Extra Tips**:
(Optional practical suggestions)

**Recommended Questions**
(Optional recommended questions based on the user's question)"""


    return prompt


# =============================================================================
# Azure OpenAI API call for response generation
# =============================================================================

def generate_response(prompt: str, api_key: str = AZURE_API_KEY) -> Optional[str]:
    """Call Azure OpenAI chat completion API and return the assistant message."""
    try:
        if not api_key or api_key.strip() == "":
            return None

        client = AzureOpenAI(
            api_key=api_key,
            api_version="2024-10-21",
            azure_endpoint=AZURE_ENDPOINT,
        )

        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional travel advisor familiar with Lonely Planet guides. "
                    "Provide concise, practical travel advice based on the given context.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1500,
        )

        return response.choices[0].message.content

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Authentication" in error_msg or "invalid" in error_msg.lower():
            return None
        return f"Error: {error_msg}"


# =============================================================================
# Sidebar: destinations list, options, and API config
# =============================================================================

def render_sidebar(available_countries: List[str], cover_picture_path: Path):
    """Render sidebar with destination covers, search options, and API settings."""
    st.markdown(
        """<style> section[data-testid="stSidebar"] .stImage img {
            width: 100% !important; max-width: 100% !important; object-fit: contain;
        } </style>""",
        unsafe_allow_html=True,
    )
    st.subheader("Available Destinations")
    for country in available_countries:
        with st.container():
            st.caption(f"**{country}**")
            cover_file = cover_image_path(cover_picture_path, country)
            if cover_file is not None:
                st.image(str(cover_file), width="stretch")
            else:
                st.info(f"No cover for {country}")

    st.divider()
    st.subheader("Advanced Options")
    search_top_k = st.slider(
        "Retrieve top K segments",
        3,
        15,
        5,
        help="Number of context chunks to retrieve per query.",
    )
    use_llm = st.toggle(
        "Enable AI Recommendations",
        value=True,
        help="Use Azure OpenAI for response generation.",
    )

    st.subheader("Azure OpenAI Configuration")
    api_key_input = st.text_input(
        "API Key",
        value=AZURE_API_KEY,
        type="password",
        placeholder="Paste your Azure OpenAI API key",
        help="Primary or Secondary key from Azure.",
    )
    show_debug = st.toggle(
        "Show Debug Info",
        value=False,
        help="Display retrieval statistics.",
    )

    st.divider()
    st.info(
        "**Knowledge Base Source:** Lonely Planet Publications\n\n"
        "**AI Engine:** HKUST OpenAI Azure API\n\n"
        "**Email:** katiexu0117@gmail.com"
    )

    return search_top_k, use_llm, api_key_input, show_debug


# =============================================================================
# Main content: destination selector and book picture viewer
# =============================================================================

def render_destination_panel(available_countries: List[str], cover_picture_path: Path):
    """Render left column with country selector and book picture gallery."""
    st.subheader("Step1. Choose Destination")
    selected_country = st.selectbox(
        "Select a country:",
        available_countries,
        index=0,
        label_visibility="collapsed",
    )

    if selected_country:
        kb = load_knowledge_base(selected_country)
        if kb:
            with st.container(border=True):
                col1, col2 = st.columns(2)
                col1.metric("Source Data", kb.get("total_characters", 0), "characters")
                col2.metric("Segments", len(kb["chunks"]))

        image_carousel(selected_country, key="main_carousel")

    return selected_country


# =============================================================================
# Search results and AI response display
# =============================================================================

def render_search_results(
    query: str,
    selected_country: str,
    results: List[Dict],
    scores: np.ndarray,
    keywords: List[str],
    use_llm: bool,
    api_key_input: str,
    search_top_k: int,
    show_debug: bool,
):
    """Render search results, AI recommendations, and source documents."""
    st.divider()

    if use_llm:
        with st.spinner("Generating response..."):
            prompt = build_rag_prompt(query, results)
            answer = generate_response(prompt, api_key_input)

            if answer is None:
                st.info(
                    "**Azure OpenAI not configured.** Showing source documents.\n\n"
                    "Configure API Key in the sidebar to enable AI responses."
                )
            elif answer and not answer.startswith("Error"):
                st.subheader("AI-Powered Recommendations")
                st.markdown(answer)
            else:
                st.warning(answer)

    st.subheader("Source Documents")

    if len(results) > 1:
        tabs = st.tabs([f"Result {i + 1}" for i in range(len(results))])
        for tab, res in zip(tabs, results):
            with tab:
                col_rel1, col_rel2 = st.columns([3, 1])
                col_rel1.progress(res["similarity"], text=f"Relevance: {res['relevance_pct']}")
                col_rel2.caption(f"Page {res['page']}")
                st.markdown(f"**Excerpt:**\n{res['text']}")
                with st.expander("View full segment"):
                    st.write(res["text"])
                    st.caption(f"Chunk ID: {res['chunk_id']}")
    else:
        for res in results:
            with st.container(border=True):
                col_rel1, col_rel2 = st.columns([3, 1])
                col_rel1.progress(res["similarity"], text=f"Relevance: {res['relevance_pct']}")
                col_rel2.caption(f"Page {res['page']}")
                st.markdown(f"**Excerpt:**\n{res['text']}")
                with st.expander("View full segment"):
                    st.write(res["text"])
                    st.caption(f"Chunk ID: {res['chunk_id']}")

    if show_debug:
        st.divider()
        with st.expander("Debug Information"):
            debug_info = {
                "query": query,
                "country": selected_country,
                "retrieved_segments": len(results),
                "top_k_requested": search_top_k,
                "average_similarity": float(np.mean(scores)),
                "min_similarity": float(np.min(scores)),
                "max_similarity": float(np.max(scores)),
                "keywords_extracted": keywords,
                "llm_enabled": use_llm,
                "azure_api_configured": bool(api_key_input and len(api_key_input) > 10),
            }
            st.json(debug_info)


# =============================================================================
# Travel Plan Generation and Recommendation Functions
# =============================================================================

def _process_single_attraction(
    idx: int,
    result: Dict,
    country: str,
    preferences: List[str],
    api_key: str,
    colors: List[str]
) -> Optional[Dict]:
    """Process a single attraction (used for parallel execution)."""
    try:
        raw_text = result["text"]
        
        # Extract attraction name
        lines = raw_text.split('\n')
        attraction_name = lines[0].strip() if lines else f"Attraction {country}"
        attraction_name = attraction_name.replace('**', '').replace('##', '').strip()
        if len(attraction_name) > 100:
            attraction_name = attraction_name[:80] + "..."
        
        # Generate BOTH title and description in parallel threads
        # But since we're already in a thread, we'll call them sequentially
        short_title = generate_short_title(attraction_name, raw_text[:600], api_key)
        ai_description = generate_ai_enhanced_description(
            attraction_name, raw_text[:800], preferences, api_key
        )
        
        # Fetch images for the attraction using Google Images via Outscraper
        images = []
        try:
            search_query = f"{attraction_name} {country}"
            images = fetch_pexels_images(search_query, per_page=3)  # Now uses Outscraper Google Images
        except Exception as e:
            print(f"⚠️ Failed to fetch images for {attraction_name}: {str(e)}")
        
        return {
            "id": idx,
            "name": attraction_name,
            "short_title": short_title if short_title else attraction_name,
            "description": ai_description if ai_description else raw_text[:500],
            "raw_text": raw_text,
            "page": result["page"],
            "relevance": result["relevance_pct"],
            "selected": False,
            "color": colors[idx % len(colors)],
            "images": images
        }
    except Exception as e:
        return None


def get_attractions_recommendations(
    country: str,
    preferences: List[str],
    api_key: str = AZURE_API_KEY,
    top_k: int = 10
) -> List[Dict]:
    """Get AI-recommended attractions based on preferences using RAG with parallel processing."""
    kb = load_knowledge_base(country)
    if not kb:
        return []
    
    # Build query from preferences
    pref_query = f"Best attractions for {', '.join(preferences)} in {country}"
    
    results, scores = semantic_search(pref_query, country, top_k=top_k)
    
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
        "#F7DC6F", "#BB8FCE", "#85C1E2", "#F8B88B", "#AED6F1"
    ]
    
    attractions = []
    
    # Use ThreadPoolExecutor for parallel API calls
    max_workers = min(5, len(results[:10]))  # Limit to 5 concurrent threads
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(
                _process_single_attraction,
                i, result, country, preferences, api_key, colors
            ): i for i, result in enumerate(results[:10])
        }
        
        # Collect results as they complete
        for future in as_completed(futures):
            attr = future.result()
            if attr:
                attractions.append(attr)
    
    # Sort by original order
    attractions.sort(key=lambda x: x["id"])
    
    return attractions


def generate_short_title(
    attraction_name: str,
    context_text: str,
    api_key: str = AZURE_API_KEY
) -> Optional[str]:
    """Generate a concise, engaging title with location and timing (< 10 words)."""
    try:
        if not api_key or api_key.strip() == "":
            return None
        
        prompt = f"""Create a SHORT, catchy title for this attraction in LESS than 10 words. 
Must include: location name, best time to visit.
Keep it elegant and appealing.

Attraction: {attraction_name}
Context: {context_text[:300]}

Format: Just the title, nothing else. No quotes, no explanation.
Example: "Paris at Sunset - The Iron Lady's Golden Hour"
"""

        client = AzureOpenAI(
            api_key=api_key,
            api_version="2024-10-21",
            azure_endpoint=AZURE_ENDPOINT,
        )

        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a creative travel copywriter. Generate SHORT, punchy, elegant titles for tourist attractions.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.9,
            max_tokens=30,
        )

        title = response.choices[0].message.content.strip()
        # Ensure it's under 10 words
        words = title.split()
        if len(words) > 10:
            title = " ".join(words[:10])
        return title
        
    except Exception as e:
        return None


def generate_ai_enhanced_description(
    attraction_name: str,
    context_text: str,
    preferences: List[str],
    api_key: str = AZURE_API_KEY
) -> Optional[str]:
    """Generate engaging description using Azure OpenAI."""
    try:
        if not api_key or api_key.strip() == "":
            return None
        
        prompt = f"""Based on this travel information about {attraction_name}, write a short, engaging 2-3 sentence description for travelers interested in: {', '.join(preferences)}.

Travel Information:
{context_text}

Requirements:
1. Make it exciting and appealing to travelers
2. Highlight unique features relevant to their interests
3. Include one practical tip
4. Use 2-3 sentences max
5. Write in a friendly, conversational tone
6. Start with an emoji that matches the attraction

Format: 
[emoji] [Description with practical tip]"""

        client = AzureOpenAI(
            api_key=api_key,
            api_version="2024-10-21",
            azure_endpoint=AZURE_ENDPOINT,
        )

        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a creative travel writer who writes engaging, inspiring descriptions of tourist attractions. Keep descriptions concise but compelling.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=200,
        )

        return response.choices[0].message.content
        
    except Exception as e:
        return None


def generate_itinerary(
    days: int,
    attractions: List[Dict],
    budget: float,
    preferences: List[str],
    api_key: str = AZURE_API_KEY
) -> str:
    """Generate detailed itinerary with structured day-by-day breakdowns using LLM."""
    attraction_list = "\n".join([
        f"- **{a['name']}**: {a['description'][:200]}"
        for a in attractions if a.get('selected', False)
    ])
    
    prompt = f"""Create a detailed, enthusiastic {days}-day travel itinerary with the following structure. 
Make it exciting and inspiring with plenty of emojis!

Budget per person: ${budget}/day
Preferences: {', '.join(preferences)}
Selected Attractions:
{attraction_list}

CRITICAL FORMAT REQUIREMENTS:
For each day, provide with this EXACT structure (must have these exact headers):

**Day 1: [Day Theme/Title with emoji]**

🌅 **Morning**:
- **[Attraction Name]**: [Detailed description with emoji bullet points]
- **[Activity/Attraction]**: [Description with practical tips and times]

☀️ **Afternoon**:
- **[Attraction Name]**: [Detailed description with emoji bullet points]
- **[Activity/Attraction]**: [Description with practical tips and times]

🌙 **Evening**:
- **[Dining/Activity]**: [Enthusiastic description of restaurant/activity with recommendations]
- **[Attraction]**: [Optional evening activity with timing]

⚠️ **Important Notes**:
- [Tip 1 with emoji]
- [Tip 2 with emoji]
- [Local info with emoji]

💰 **Budget Estimate**: $[amount] (accommodation/food/activities breakdown)

---

Repeat this structure for each day (Day 2, Day 3, etc.)

TONE & STYLE:
- Use 🌟✨🎭🏖️🎨🍜🏛️ emojis generously
- Be enthusiastic and warm
- Use bullet points for easy reading
- Bold attraction names with **Name**
- Include specific times, prices when possible
- Add insider tips and practical advice
- Make it feel like a friend recommending places

FINAL SECTION:
After all days, provide:

**Overall Budget Summary**:
- Total accommodation cost
- Total food/dining budget
- Total transportation
- Total activities/attractions
- Contingency budget
- **TOTAL TRIP COST**: $[amount]

Make this itinerary inspiring, detailed, practical, and exciting!"""

    try:
        if not api_key or api_key.strip() == "":
            return "API Key not configured"

        client = AzureOpenAI(
            api_key=api_key,
            api_version="2024-10-21",
            azure_endpoint=AZURE_ENDPOINT,
        )

        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are an enthusiastic, expert travel planner who creates inspiring, detailed, and practical itineraries with lots of emojis and warm personalization. You provide insider tips and make travel recommendations feel like advice from a trusted friend.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=3000,
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error generating itinerary: {str(e)}"


def create_excel_export(
    trip_data: Dict,
    itinerary: str,
    filename: str = "travel_plan.xlsx"
) -> Optional[bytes]:
    """Create Excel file with trip details and weather data in day columns."""
    if not HAS_OPENPYXL:
        st.warning("openpyxl not installed. Please install: pip install openpyxl")
        return None
    
    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Trip Plan"
        
        # Style definitions
        header_fill = PatternFill(start_color="DC2626", end_color="DC2626", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        title_font = Font(bold=True, size=14, color="DC2626")
        date_font = Font(bold=True, size=11, color="FFFFFF")
        date_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
        weather_font = Font(size=10)
        weather_fill = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")
        content_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        content_font = Font(size=9)
        
        # Title
        ws['A1'] = "🌍 TRAVEL PLAN"
        ws['A1'].font = title_font
        ws.merge_cells('A1:M1')
        
        # Trip Details (left side info)
        row = 3
        ws[f'A{row}'] = "Trip Details"
        ws[f'A{row}'].font = Font(bold=True, size=11, color="DC2626")
        row += 1
        
        start_date = trip_data.get('start_date')
        end_date = trip_data.get('end_date')
        destination = trip_data.get('destination', 'Unknown')
        
        ws[f'A{row}'] = f"Destination: {destination}"
        row += 1
        if start_date:
            ws[f'A{row}'] = f"Start Date: {start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else start_date}"
            row += 1
        if end_date:
            ws[f'A{row}'] = f"End Date: {end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else end_date}"
            row += 1
        
        ws[f'A{row}'] = f"Travelers: {trip_data.get('travelers', 1)}"
        row += 1
        ws[f'A{row}'] = f"Budget: ${trip_data.get('budget', 'N/A')}/day/person"
        row += 1
        
        # Preferences
        row += 1
        ws[f'A{row}'] = "Preferences:"
        ws[f'A{row}'].font = Font(bold=True)
        row += 1
        for pref in trip_data.get('preferences', []):
            ws[f'A{row}'] = f"• {pref}"
            row += 1
        
        # Parse itinerary to extract day-by-day content
        days_data = {}
        lines = itinerary.split('\n')
        current_day = None
        current_content = []
        
        import re
        for line in lines:
            if re.match(r'\*\*Day\s+(\d+)\*\*|\*\*Day\s+(\d+):', line):
                if current_day is not None and current_content:
                    days_data[current_day] = '\n'.join(current_content).strip()
                
                match = re.search(r'Day\s+(\d+)', line)
                if match:
                    current_day = int(match.group(1))
                    current_content = []
            elif current_day is not None and line.strip() and 'Budget' not in line:
                # Clean up markdown formatting
                cleaned = line.replace('**', '').replace('- ', '').strip()
                if cleaned:
                    current_content.append(cleaned)
        
        if current_day is not None and current_content:
            days_data[current_day] = '\n'.join(current_content).strip()
        
        # Get country coordinates for weather
        country_coords = get_country_coordinates(destination) if destination else (0, 0)
        
        # Calculate number of days
        num_days = 0
        if start_date and end_date:
            if hasattr(start_date, 'date'):
                start_date = start_date.date()
            if hasattr(end_date, 'date'):
                end_date = end_date.date()
            num_days = (end_date - start_date).days + 1
        
        # Create day-based columns
        day_row = 3  # Row for day headers
        
        if num_days > 0 and start_date:
            # Day headers row
            for day_idx in range(num_days):
                col = chr(66 + day_idx)  # B, C, D, ...
                current_date = start_date + timedelta(days=day_idx)
                day_label = f"Day {day_idx + 1}"
                
                ws[f'{col}{day_row}'] = day_label
                ws[f'{col}{day_row}'].font = date_font
                ws[f'{col}{day_row}'].fill = date_fill
                ws[f'{col}{day_row}'].alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            
            # Date row
            date_row = day_row + 1
            for day_idx in range(num_days):
                col = chr(66 + day_idx)
                current_date = start_date + timedelta(days=day_idx)
                date_str = current_date.strftime('%Y-%m-%d')
                
                ws[f'{col}{date_row}'] = date_str
                ws[f'{col}{date_row}'].font = weather_font
                ws[f'{col}{date_row}'].fill = weather_fill
                ws[f'{col}{date_row}'].alignment = Alignment(horizontal='center')
            
            # Add day content (activities) directly
            content_start_row = date_row + 1
            
            # Add day content (activities)
            for day_idx in range(num_days):
                col = chr(66 + day_idx)
                day_num = day_idx + 1
                
                day_content = days_data.get(day_num, f"Day {day_num} activities")
                
                ws[f'{col}{content_start_row}'] = day_content
                ws[f'{col}{content_start_row}'].alignment = Alignment(wrap_text=True, vertical='top')
                ws[f'{col}{content_start_row}'].font = content_font
                ws[f'{col}{content_start_row}'].fill = content_fill
            
            # Set column widths
            ws.column_dimensions['A'].width = 25
            for day_idx in range(num_days):
                col = chr(66 + day_idx)
                ws.column_dimensions[col].width = 18
            
            # Set row height for content
            ws.row_dimensions[content_start_row].height = 100
        
        # Save to bytes
        import io
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        return excel_buffer.getvalue()
        
    except Exception as e:
        st.error(f"Error creating Excel: {str(e)}")
        import traceback
        st.error(f"Details: {traceback.format_exc()}")
        return None


def send_email(recipient: str, subject: str, body: str, attachment_bytes: Optional[bytes] = None) -> Tuple[bool, str]:
    """Send email via Gmail SMTP with App Password."""
    import socket
    
    if not HAS_EMAIL:
        return False, "❌ Email libraries not available"
    
    try:
        # Gmail SMTP Configuration - using App Password (not account password)
        SMTP_SERVER = "smtp.gmail.com"
        SMTP_PORT = 587
        SENDER_EMAIL = "katiexu0117@gmail.com"
        SENDER_PASSWORD = "yazojnyiavnwmchb"
        
        # Validate inputs
        if not recipient or '@' not in recipient:
            return False, "❌ Invalid email address"
        
        if not SENDER_PASSWORD or len(SENDER_PASSWORD) < 8:
            return False, "❌ Email not configured"
        
        msg = MIMEMultipart('alternative')
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient
        msg['Subject'] = subject
        msg['Date'] = time.strftime('%a, %d %b %Y %H:%M:%S %z')
        
        msg.attach(MIMEText(body.replace('\n', '<br>'), 'html', _charset='UTF-8'))
        
        if attachment_bytes:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment_bytes)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="travel_plan.xlsx"')
            msg.attach(part)
        
        server = None
        try:
            # Try to connect with extended timeout
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20)
            server.set_debuglevel(0)
            server.starttls(timeout=20)
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()
            return True, f"✅ Email sent to {recipient}"
            
        except socket.timeout:
            return False, "⚠️ Email service timeout (network issue) - try downloading Excel instead"
        except smtplib.SMTPAuthenticationError:
            return False, "⚠️ Email auth failed - check credentials"
        except smtplib.SMTPServerDisconnected:
            return False, "⚠️ Connection lost - try again"
        except Exception as e:
            error_msg = str(e)[:50]
            return False, f"⚠️ Email error: {error_msg}"
        finally:
            if server:
                try:
                    server.quit()
                except:
                    pass
            
    except Exception as e:
        return False, f"⚠️ System error: {str(e)[:50]}"


def format_itinerary_email(itinerary: str, destination: str, days: int) -> str:
    """Format itinerary with warm greeting, body, poem, and signature."""
    
    # 新的邮件开场白
    greeting = f"""Dear Friend,

Happy to hear about your travel plan. The outcome has been attached for your further use!

This carefully crafted {days}-day journey through {destination} has been designed with love and expertise to give you unforgettable memories and authentic experiences.

Whether you're seeking adventure, relaxation, culture, or culinary delights, we've woven them all into this special itinerary just for you.

---

"""

    # 新的旅行诗歌
    travel_poem = """

---

**The Wanderer's Heart**

Pack light but dream heavy, the world calls your name,
From mountains to cities, each place is the same—
A mirror for souls who dare to explore,
A chance to discover what you came looking for.

Markets and temples, old streets and new faces,
The sweet smell of danger in all unknown places,
You'll find yourself changing with every new mile,
Coming home through the world with a deeper smile.

So wander, dear friend, let the journey be true,
The adventures ahead are all waiting for you,
For life is not measured by years that we live,
But by the brave moments we choose to forgive.

Return home with stories that stir up the soul,
A traveler's truth is that journeys make whole.

---

"""

    # 发信人落款（简化）
    signature = """
Warm regards,

Your Loved Lonely Planet
Your Personal Travel Companion

---
*Every journey tells a story. Make yours unforgettable.*
"""

    return greeting + itinerary + travel_poem + signature


def send_email_via_rapidapi(recipient: str, subject: str, body: str) -> Tuple[bool, str]:
    """Send email via Simple Email Service API (more reliable than mail-sender-api1)."""
    if not HAS_REQUESTS:
        return False, "Error: requests library not available"
    
    try:
        # Using SendGrid's alternative: simple email-js service
        url = "https://www.emailjs.com/api/v1.0/email/send"
        
        # Clean body for email
        clean_body = body.replace('<br>', '\n').replace('**', '').replace('##', '')
        
        # EmailJS Parameters
        payload = {
            "service_id": "service_default",
            "template_id": "template_default",
            "user_id": "default_public",
            "template_params": {
                "to_email": recipient,
                "from_email": "katiexu0117@gmail.com",
                "subject": subject,
                "message": clean_body,
                "reply_to": "katiexu0117@gmail.com"
            }
        }
        
        headers = {
            'Content-Type': "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            return True, f"✅ Email sent successfully to {recipient}"
        elif response.status_code in [400, 401, 403, 404]:
            # Fallback: Try to send via the basic SMTP method
            return send_email_via_smtp(recipient, subject, body)
        else:
            return False, f"❌ Failed to send email. Status: {response.status_code}. Response: {response.text[:200]}"
            
    except Exception as e:
        # Fallback to SMTP method if EmailJS fails
        print(f"EmailJS failed: {str(e)}, trying SMTP fallback...")
        return send_email_via_smtp(recipient, subject, body)


def send_email_via_smtp(recipient: str, subject: str, body: str) -> Tuple[bool, str]:
    """Fallback: Send email via Gmail SMTP using App Password."""
    if not HAS_EMAIL:
        return False, "Error: Email libraries not installed. Install: pip install secure-smtplib"
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        SMTP_SERVER = "smtp.gmail.com"
        SMTP_PORT = 587
        SENDER_EMAIL = "katiexu0117@gmail.com"
        # Gmail App Password - get from https://myaccount.google.com/apppasswords
        SENDER_PASSWORD = "yazojnyiavnwmchb"  # Updated  
        
        if not recipient or '@' not in recipient:
            return False, "Invalid recipient email address"
        
        msg = MIMEMultipart('alternative')
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient
        msg['Subject'] = subject
        
        # Add body as HTML
        clean_body = body.replace('\n', '<br>')
        msg.attach(MIMEText(clean_body, 'html', _charset='UTF-8'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True, f"✅ Email sent successfully to {recipient}"
        
    except smtplib.SMTPAuthenticationError:
        return False, "⚠️ Gmail authentication failed. Get App Password: https://myaccount.google.com/apppasswords"
    except Exception as e:
        return False, f"❌ SMTP Error: {str(e)}"


def display_itinerary_as_table(itinerary_text: str):
    """Parse and display itinerary as a structured table."""
    import pandas as pd
    import re
    
    # Parse itinerary by days and time periods
    lines = itinerary_text.split('\n')
    days_schedule = {}
    current_day = None
    current_period = None
    current_content = []
    
    for line in lines:
        # Check if it's a day header
        day_match = re.search(r'\*\*Day\s+(\d+)[:\s]', line)
        if day_match:
            if current_day and current_period and current_content:
                if current_day not in days_schedule:
                    days_schedule[current_day] = {}
                days_schedule[current_day][current_period] = '\n'.join(current_content).strip()
            
            current_day = f"Day {day_match.group(1)}"
            current_period = None
            current_content = []
            continue
        
        # Check for time periods (Morning, Afternoon, Evening)
        if current_day:
            if '🌅 **Morning**' in line or '**Morning**' in line:
                if current_period and current_content:
                    if current_day not in days_schedule:
                        days_schedule[current_day] = {}
                    days_schedule[current_day][current_period] = '\n'.join(current_content).strip()
                current_period = 'Morning'
                current_content = []
            elif '☀️ **Afternoon**' in line or '**Afternoon**' in line:
                if current_period and current_content:
                    if current_day not in days_schedule:
                        days_schedule[current_day] = {}
                    days_schedule[current_day][current_period] = '\n'.join(current_content).strip()
                current_period = 'Afternoon'
                current_content = []
            elif '🌙 **Evening**' in line or '**Evening**' in line:
                if current_period and current_content:
                    if current_day not in days_schedule:
                        days_schedule[current_day] = {}
                    days_schedule[current_day][current_period] = '\n'.join(current_content).strip()
                current_period = 'Evening'
                current_content = []
            elif current_period and line.strip() and not line.strip().startswith('⚠️') and not line.strip().startswith('💰'):
                # Add content to current period
                cleaned = line.replace('**', '').replace('- ', '• ').strip()
                if cleaned and 'Important Notes' not in cleaned and 'Budget Estimate' not in cleaned:
                    current_content.append(cleaned)
    
    # Save last content
    if current_day and current_period and current_content:
        if current_day not in days_schedule:
            days_schedule[current_day] = {}
        days_schedule[current_day][current_period] = '\n'.join(current_content).strip()
    
    if not days_schedule:
        st.markdown(itinerary_text)
        return
    
    # Create table data
    table_data = []
    periods = ['Morning', 'Afternoon', 'Evening']
    
    for day_num in range(1, 10):
        day_key = f"Day {day_num}"
        if day_key in days_schedule:
            row = [day_key]
            for period in periods:
                content = days_schedule[day_key].get(period, '')
                row.append(content)
            table_data.append(row)
    
    if table_data:
        # Display as HTML table
        html_table = '<table style="width:100%; border-collapse: collapse; margin: 20px 0;">'
        html_table += '<thead style="background-color: #000000; color: white;">'
        html_table += '<tr style="border: 1px solid #444;">'
        html_table += '<th style="padding: 12px; text-align: left; border: 1px solid #444; font-weight: bold;">Day</th>'
        for period in periods:
            html_table += f'<th style="padding: 12px; text-align: left; border: 1px solid #444; font-weight: bold;">{period}</th>'
        html_table += '</tr></thead>'
        
        html_table += '<tbody>'
        for row_idx, row in enumerate(table_data):
            bg_color = '#1a1a1a' if row_idx % 2 == 0 else '#0d0d0d'
            html_table += f'<tr style="background-color: {bg_color}; border: 1px solid #444; color: white;">'
            html_table += f'<td style="padding: 12px; border: 1px solid #444; font-weight: bold; min-width: 80px; color: white;">{row[0]}</td>'
            for content in row[1:]:
                html_table += f'<td style="padding: 12px; border: 1px solid #444; vertical-align: top; font-size: 13px; line-height: 1.6; color: white;">'
                html_table += content.replace('\n', '<br>')
                html_table += '</td>'
            html_table += '</tr>'
        html_table += '</tbody>'
        html_table += '</table>'
        
        st.markdown(html_table, unsafe_allow_html=True)
    
    # Show budget breakdown if present
    if 'Budget' in itinerary_text:
        st.divider()
        st.subheader("💰 Budget Summary")
        budget_section = itinerary_text.split('**Overall Budget Summary**')[-1] if '**Overall Budget Summary**' in itinerary_text else ""
        if budget_section:
            # Clean up budget text
            budget_text = budget_section.split('**Recommended Questions**')[0] if '**Recommended Questions**' in budget_section else budget_section
            st.markdown(budget_text)


def display_itinerary_as_cards(itinerary_text: str):
    """Parse and display itinerary as cards instead of bullet points."""
    
    # Parse itinerary by days
    lines = itinerary_text.split('\n')
    days_data = {}
    current_day = None
    current_content = []
    
    for line in lines:
        # Check if it's a day header (e.g., "**Day 1**: ..." or "Day 1:")
        if line.strip().startswith('**Day') or line.strip().startswith('Day '):
            if current_day and current_content:
                days_data[current_day] = '\n'.join(current_content).strip()
            
            # Extract day number
            import re
            match = re.search(r'Day\s+(\d+)', line)
            if match:
                current_day = f"Day {match.group(1)}"
            current_content = []
        elif current_day:
            # Add to current day's content, but skip bullet points formatting
            if line.strip() and not line.strip().startswith('**Budget'):
                # Remove markdown formatting
                cleaned = line.replace('**', '').replace('- ', '').strip()
                if cleaned:
                    current_content.append(cleaned)
    
    # Don't forget the last day
    if current_day and current_content:
        days_data[current_day] = '\n'.join(current_content).strip()
    
    if not days_data:
        st.markdown(itinerary_text)
        return
    
    # Display as cards
    st.markdown("""
    <style>
    .day-card {
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transition: transform 0.2s;
    }
    .day-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.2);
    }
    .day-title {
        font-size: 20px;
        font-weight: 700;
        margin-bottom: 12px;
        border-bottom: 2px solid rgba(255,255,255,0.3);
        padding-bottom: 10px;
    }
    .day-content {
        font-size: 14px;
        line-height: 1.8;
        white-space: pre-wrap;
    }
    </style>
    """, unsafe_allow_html=True)
    
    for day, content in days_data.items():
        card_html = f"""
        <div class="day-card">
            <div class="day-title">{day}</div>
            <div class="day-content">{content}</div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
    
    
    # Show budget breakdown if present
    if 'Budget Breakdown' in itinerary_text or 'budget' in itinerary_text.lower():
        st.divider()
        st.subheader("Budget Breakdown")
        budget_section = itinerary_text.split('**Budget')[-1] if '**Budget' in itinerary_text else ""
        if budget_section:
            st.markdown(budget_section)


def get_country_coordinates(country_name: str) -> Tuple[float, float]:
    """Get latitude and longitude for a country (capital city)."""
    coordinates = {
        "Austria": (48.2082, 16.3738),  # Vienna
        "Cambodia": (11.5564, 104.9282),  # Phnom Penh
        "China": (39.9042, 116.4074),  # Beijing
        "Cuba": (23.1291, -82.3794),  # Havana
        "Estonia": (59.4370, 24.7536),  # Tallinn
        "Estonia, Latvia, Lithuania": (55.1694, 24.8383),  # Vilnius
        "Europe": (50.1109, 8.6821),  # Frankfurt
        "Iran": (35.6892, 51.3889),  # Tehran
        "Italy": (41.9028, 12.4964),  # Rome
        "Malaysia": (3.1390, 101.6869),  # Kuala Lumpur
        "Malaysia, Singapore, Brunei": (1.3521, 103.8198),  # Singapore
        "Poland": (52.2297, 21.0122),  # Warsaw
        "Thailand": (13.7563, 100.5018),  # Bangkok
        "West Africa": (6.8276, -5.2893),  # Accra
        "Zambia": (-10.8355, 34.5199),  # Lusaka
        "Zambia, Mozambique, Malawi": (-15.3875, 28.2882),  # Lilongwe
    }
    
    lat, lon = coordinates.get(country_name, (20.0, 0.0))
    return lat, lon


# Weather functionality removed per user request


# Weather data function removed per user request


# =============================================================================
# Travel Plan Page Rendering
# =============================================================================

def render_get_plan_page():
    """Render the 'Get Your Plan' page to view and share the generated plan."""
    display_top_banner("📋 Get Your Plan")
    st.caption("View your personalized travel itinerary and share it via email")
    
    # Check if there's a generated itinerary
    if "plan_data" not in st.session_state or "generated_itinerary" not in st.session_state:
        st.info("👈 Please generate an itinerary first using the 'Create Plan' tab!")
        st.stop()
    
    plan_data = st.session_state.plan_data
    itinerary = st.session_state.generated_itinerary
    
    # === Display Plan Summary ===
    st.divider()
    st.subheader("✈️ Your Trip Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🌍 Destination", plan_data.get("destination", "N/A"))
    with col2:
        days = (plan_data.get("end_date", datetime.now().date()) - plan_data.get("start_date", datetime.now().date())).days + 1
        st.metric("📅 Duration", f"{days} days")
    with col3:
        st.metric("👥 Travelers", plan_data.get("travelers", 1))
    with col4:
        budget = plan_data.get("budget", 0)
        total_budget = budget * days * plan_data.get("travelers", 1)
        st.metric("💰 Total Budget", f"${total_budget:,}")
    
    # === Display Trip Details ===
    st.divider()
    st.subheader("🎯 Trip Details")
    
    col1, col2 = st.columns(2)
    with col1:
        start = plan_data.get("start_date")
        if hasattr(start, 'strftime'):
            start_str = start.strftime('%B %d, %Y')
        else:
            start_str = str(start)
        st.write(f"**Start Date:** {start_str}")
    
    with col2:
        end = plan_data.get("end_date")
        if hasattr(end, 'strftime'):
            end_str = end.strftime('%B %d, %Y')
        else:
            end_str = str(end)
        st.write(f"**End Date:** {end_str}")
    
    # Display preferences
    prefs = plan_data.get("preferences", [])
    if prefs:
        prefs_text = ", ".join(prefs)
        st.write(f"**Preferences:** {prefs_text}")
    
    st.write(f"**Daily Budget per Person:** ${plan_data.get('budget', 0)}/day")
    
    # === Display Selected Attractions ===
    attractions = plan_data.get("selected_attractions", [])
    if attractions:
        st.divider()
        st.subheader(f"🏛️ Selected Attractions ({len(attractions)})")
        
        for i, attr in enumerate(attractions, 1):
            st.write(f"{i}. **{attr.get('name', 'Attraction')}** - Page {attr.get('page', 'N/A')}")
    
    # === Display Full Itinerary ===
    st.divider()
    st.subheader("📝 Your Detailed Itinerary")
    
    display_itinerary_as_table(itinerary)
    
    # === Email Sharing Section ===
    st.divider()
    st.subheader("✉️ Share Your Plan")
    st.caption("Send your travel plan via email")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📧 Send to Casey's Admin")
        st.info("Automatically send to: **Casey.xu.2021@outlook.com**")
        
        if st.button("🚀 Send to Admin", use_container_width=True, key="send_to_admin"):
            with st.spinner("Sending email to admin..."):
                # Calculate days and format email
                start = plan_data.get("start_date")
                end = plan_data.get("end_date")
                if hasattr(start, 'date'):
                    start = start.date()
                if hasattr(end, 'date'):
                    end = end.date()
                num_days = (end - start).days + 1 if (end and start) else 0
                
                formatted_itinerary = format_itinerary_email(
                    itinerary,
                    plan_data.get('destination', 'Your Destination'),
                    num_days
                )
                
                success, message = send_email_via_rapidapi(
                    "Casey.xu.2021@outlook.com",
                    f"✈️ Travel Plan: {plan_data.get('destination', 'Travel')} ({datetime.now().strftime('%Y-%m-%d')})",
                    formatted_itinerary
                )
                
                if success:
                    st.success(message)
                    st.balloons()
                else:
                    st.error(message)
    
    with col2:
        st.markdown("### 📥 Get Your Own Copy")
        st.write("Download and/or email to yourself")
        
        email_input = st.text_input(
            "Your Email Address",
            placeholder="your.email@example.com",
            key="user_email_input",
            label_visibility="collapsed"
        )
        
        col_download, col_send = st.columns(2)
        
        with col_download:
            if st.button("⬇️ Download Excel", use_container_width=True, key="download_excel_get"):
                excel_data = create_excel_export(
                    plan_data,
                    itinerary
                )
                
                if excel_data:
                    st.download_button(
                        label="💾 Get Excel File",
                        data=excel_data,
                        file_name=f"travel_plan_{plan_data.get('destination', 'trip')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
        
        with col_send:
            if st.button("✉️ Send to Me", use_container_width=True, key="send_to_me"):
                if email_input and "@" in email_input:
                    with st.spinner(f"Sending email to {email_input}..."):
                        # Calculate days and format email
                        start = plan_data.get("start_date")
                        end = plan_data.get("end_date")
                        if hasattr(start, 'date'):
                            start = start.date()
                        if hasattr(end, 'date'):
                            end = end.date()
                        num_days = (end - start).days + 1 if (end and start) else 0
                        
                        formatted_itinerary = format_itinerary_email(
                            itinerary,
                            plan_data.get('destination', 'Your Destination'),
                            num_days
                        )
                        
                        success, message = send_email_via_rapidapi(
                            email_input,
                            f"✈️ Your Travel Plan: {plan_data.get('destination', 'Travel')} ({datetime.now().strftime('%Y-%m-%d')})",
                            formatted_itinerary
                        )
                        
                        if success:
                            st.success(message)
                            st.balloons()
                        else:
                            st.error(message)
                else:
                    st.warning("⚠️ Please enter a valid email address")
    
    # === Additional Options ===
    st.divider()
    st.subheader("🔧 Additional Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Create New Plan", use_container_width=True, key="new_plan_btn"):
            st.session_state.current_page = "plan"
            # Reset plan data for fresh start
            if "plan_data" in st.session_state:
                del st.session_state.plan_data
            if "generated_itinerary" in st.session_state:
                del st.session_state.generated_itinerary
            st.rerun()
    
    with col2:
        if st.button("🔍 Search Again", use_container_width=True, key="search_again_btn"):
            st.session_state.current_page = "search"
            st.rerun()
    
    with col3:
        if st.button("📋 View Plan Details", use_container_width=True, key="view_details_btn"):
            st.info("Plan details are displayed above ⬆️")


def render_travel_plan_page(available_countries: List[str], api_key_input: str):
    """Render the complete travel plan creation page."""
    display_top_banner("✈️ Create Your Perfect Travel Plan")
    
    # Get selected country from session state if available
    selected_country = st.session_state.get("selected_country")
    default_destination = selected_country if selected_country and selected_country in available_countries else (available_countries[0] if available_countries else None)
    
    # Initialize session state for form data
    if "plan_data" not in st.session_state:
        st.session_state.plan_data = {
            "travelers": 1,
            "start_date": datetime.now().date(),
            "end_date": (datetime.now() + timedelta(days=7)).date(),
            "destination": default_destination,
            "preferences": [],
            "budget": 2000,
            "selected_attractions": [],
        }
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Basic Info", "Preferences", "Budget", "Attractions", "Hotels"])
    
    # ===== TAB 1: Basic Information =====
    with tab1:
        st.subheader("Basic Trip Information")
        
        col1, col2 = st.columns(2)
        with col1:
            travelers = st.number_input(
                "Number of Travelers",
                min_value=1,
                max_value=20,
                value=st.session_state.plan_data["travelers"],
                help="How many people are traveling?"
            )
            st.session_state.plan_data["travelers"] = travelers
        
        with col2:
            # Find the index of the current destination
            current_dest = st.session_state.plan_data.get("destination", default_destination)
            current_index = available_countries.index(current_dest) if current_dest and current_dest in available_countries else 0
            
            destination = st.selectbox(
                "Destination",
                available_countries,
                index=current_index,
                help="Choose your travel destination"
            )
            st.session_state.plan_data["destination"] = destination
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=st.session_state.plan_data["start_date"]
            )
            st.session_state.plan_data["start_date"] = start_date
        
        with col2:
            end_date = st.date_input(
                "End Date",
                value=st.session_state.plan_data["end_date"],
                min_value=start_date
            )
            st.session_state.plan_data["end_date"] = end_date
        
        days = (end_date - start_date).days + 1
        st.info(f"Trip Duration: **{days} days**")
    
    # ===== TAB 2: Travel Style Preferences =====
    with tab2:
        st.subheader("Travel Style Preferences")
        st.caption("Select all that apply")
        
        style_options = {
            "Cultural & History": "🏛️",
            "Food & Cuisine": "🍽️",
            "Relaxation & Beach": "🏖️",
            "Outdoor Adventure": "🥾",
            "Shopping & Entertainment": "🛍️",
            "Instagram Worthy": "📸",
            "Budget Travel": "💰",
            "Luxury Experience": "🏨",
            "Family Friendly": "👨‍👩‍👧‍👦"
        }
        
        # Custom CSS for button styling
        st.markdown("""
        <style>
        .preference-btn {
            padding: 10px 15px;
            border-radius: 8px;
            border: 2px solid #e5e7eb;
            background: white;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
            margin: 5px;
        }
        .preference-btn:hover {
            border-color: #DC2626;
            background: #fef2f2;
        }
        .preference-btn.selected {
            border-color: #DC2626;
            background: #fecaca;
            color: white;
        }
        </style>
        """, unsafe_allow_html=True)
        
        cols = st.columns(3)
        selected_preferences = []
        
        for idx, (label, emoji) in enumerate(style_options.items()):
            col = cols[idx % 3]
            if col.checkbox(f"{emoji} {label}", value=(label in st.session_state.plan_data["preferences"])):
                selected_preferences.append(label)
        
        st.session_state.plan_data["preferences"] = selected_preferences
        
        if selected_preferences:
            st.success(f"Selected: {', '.join(selected_preferences)}")
    
    # ===== TAB 3: Budget Setting =====
    with tab3:
        st.subheader("Budget & Spending")
        
        # Budget presets
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Budget", use_container_width=True, key="budget_btn"):
                st.session_state.plan_data["budget"] = 1000
        with col2:
            if st.button("Comfortable", use_container_width=True, key="comfort_btn"):
                st.session_state.plan_data["budget"] = 2500
        with col3:
            if st.button("Luxury", use_container_width=True, key="luxury_btn"):
                st.session_state.plan_data["budget"] = 5000
        
        st.divider()
        
        budget = st.slider(
            "Daily Budget per Person",
            min_value=50,
            max_value=500,
            value=int(st.session_state.plan_data["budget"]),
            step=50,
            help="Adjust your daily budget"
        )
        st.session_state.plan_data["budget"] = budget
        
        days = (st.session_state.plan_data["end_date"] - st.session_state.plan_data["start_date"]).days + 1
        total_budget = budget * days * st.session_state.plan_data["travelers"]
        
        # Budget breakdown
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Daily per Person", f"${budget}")
        col2.metric("Trip Days", days)
        col3.metric("Travelers", st.session_state.plan_data["travelers"])
        col4.metric("Total Budget", f"${total_budget}", delta=None)
    
    # ===== TAB 4: Attractions Selection =====
    with tab4:
        st.subheader("Recommended Attractions")
        st.caption(f"Based on {st.session_state.plan_data['destination']} and your preferences")
        
        if st.session_state.plan_data["preferences"]:
            if st.button("Get Recommendations", use_container_width=True, key="get_recommendations"):
                with st.spinner(f"Fetching attractions for {st.session_state.plan_data['destination']}..."):
                    attractions = get_attractions_recommendations(
                        st.session_state.plan_data["destination"],
                        st.session_state.plan_data["preferences"],
                        api_key_input,
                        top_k=10
                    )
                    
                    if attractions:
                        st.session_state.attractions = attractions
                        st.success(f"Found {len(attractions)} attractions!")
                    else:
                        st.warning("No attractions found. Try different preferences.")
        else:
            st.info("👆 Select preferences in the previous tab to get recommendations")
        
        # Display attractions
        if "attractions" in st.session_state and st.session_state.attractions:
            st.markdown("### Recommended Attractions for Your Trip")
            
            # Custom CSS for attraction cards
            st.markdown("""
            <style>
            .attraction-card {
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 16px;
                color: white;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .attraction-card:hover {
                transform: translateY(-4px);
                box-shadow: 0 8px 20px rgba(0,0,0,0.2);
            }
            .attraction-title {
                font-size: 18px;
                font-weight: 700;
                margin: 0 0 12px 0;
                letter-spacing: 0.5px;
            }
            .attraction-desc {
                font-size: 14px;
                line-height: 1.6;
                opacity: 0.95;
                margin: 12px 0;
            }
            .attraction-meta {
                font-size: 12px;
                opacity: 0.85;
                margin-top: 12px;
                display: flex;
                gap: 16px;
            }
            </style>
            """, unsafe_allow_html=True)
            
            for i, attraction in enumerate(st.session_state.attractions):
                col_select, col_card = st.columns([0.8, 9.2])
                
                with col_select:
                    selected = st.checkbox(
                        "Select",
                        value=attraction.get('selected', False),
                        key=f"attr_{i}"
                    )
                    st.session_state.attractions[i]['selected'] = selected
                
                with col_card:
                    # Create HTML card
                    card_html = f"""
                    <div class="attraction-card" style="background-color: {attraction['color']};">
                        <div class="attraction-title">{attraction['short_title']}</div>
                        <div class="attraction-desc">{attraction['description']}</div>
                        <div class="attraction-meta">
                            <span>Page {attraction['page']}</span>
                            <span>Relevance: {attraction['relevance']}</span>
                        </div>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)
                    
                    # Display images for the attraction
                    images = attraction.get('images', [])
                    if images:
                        with st.expander(f"📸 Photos ({len(images)} available)"):
                            img_cols = st.columns(min(3, len(images)))
                            for idx, img in enumerate(images):
                                col_idx = idx % 3
                                if idx > 0 and idx % 3 == 0:
                                    img_cols = st.columns(min(3, len(images) - idx))
                                    col_idx = 0
                                
                                with img_cols[col_idx]:
                                    try:
                                        st.image(img['url'], use_container_width=True)
                                        st.caption(f"📸 {img['attribution']}")
                                        st.caption(f"Source: {img['source']}")
                                    except Exception as e:
                                        st.warning(f"Could not load image: {str(e)}")
                    
                    # Expandable section for full details
                    with st.expander("More details"):
                        st.write(attraction['raw_text'])
            
            # Save selected attractions
            st.session_state.plan_data["selected_attractions"] = [
                a for a in st.session_state.attractions if a.get('selected', False)
            ]
    
    # ===== TAB 5: Hotels Recommendations =====
    with tab5:
        st.subheader("🏨 Hotel Recommendations")
        st.caption(f"Based on {st.session_state.plan_data['destination']} and your budget")
        
        if st.session_state.plan_data["destination"]:
            if st.button("🔍 Get Hotel Recommendations", use_container_width=True, key="get_hotels"):
                with st.spinner(f"Finding hotels in {st.session_state.plan_data['destination']}..."):
                    hotels_data = generate_hotels_for_city(
                        st.session_state.plan_data["destination"],
                        "Global",
                        api_key=api_key_input
                    )
                    
                    if hotels_data and hotels_data.get('hotels'):
                        st.session_state.hotels_data = hotels_data
                        st.success(f"✅ Found {hotels_data.get('total_count', 0)} hotels!")
                    else:
                        st.warning("No hotels found. Please try again.")
        else:
            st.info("👆 Select a destination in the Basic Info tab")
        
        # Display Hotels
        if "hotels_data" in st.session_state and st.session_state.hotels_data:
            hotels_data = st.session_state.hotels_data
            
            # Create tabs for different budget levels
            budget_tab, midrange_tab, luxury_tab = st.tabs([
                f"💰 Budget ({len(hotels_data.get('budget_hotels', []))})",
                f"⭐ Mid-Range ({len(hotels_data.get('midrange_hotels', []))})",
                f"👑 Luxury ({len(hotels_data.get('luxury_hotels', []))})"
            ])
            
            # Budget Hotels
            with budget_tab:
                st.markdown("### Budget Accommodations")
                for hotel in hotels_data.get('budget_hotels', []):
                    with st.expander(f"💰 {hotel.get('name', 'Hotel')} ★{hotel.get('stars', 3)} ({hotel.get('nightly_rate', 'N/A')})"):
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.markdown(f"**Rating:** ⭐ {hotel.get('rating', 'N/A')} ({hotel.get('review_count', 0)} reviews)")
                            st.markdown(f"**Introduction:**\n{hotel.get('introduction', hotel.get('description', 'No description available'))}")
                            
                            if hotel.get('highlights'):
                                st.markdown("**Highlights:**")
                                for highlight in hotel.get('highlights', []):
                                    st.markdown(f"- {highlight}")
                        
                        with col2:
                            # Display hotel images
                            images = fetch_hotel_images(
                                hotel.get('name', 'Hotel'),
                                hotels_data.get('city', ''),
                                per_page=2
                            )
                            if images:
                                img_cols = st.columns(len(images))
                                for idx, img in enumerate(images):
                                    with img_cols[idx]:
                                        try:
                                            st.image(img['url'], use_container_width=True)
                                            st.caption("🏨 Hotel photo")
                                        except:
                                            st.info("Image unavailable")
                        
                        # More details
                        with st.expander("📋 Full Details"):
                            st.markdown("**Amenities:**")
                            amenities = hotel.get('amenities', [])
                            cols_amenities = st.columns(2)
                            for idx, amenity in enumerate(amenities):
                                with cols_amenities[idx % 2]:
                                    st.markdown(f"✓ {amenity}")
                            
                            if hotel.get('guest_reviews'):
                                st.markdown("**Guest Reviews:**")
                                st.info(f"👍 Positive: {hotel['guest_reviews'].get('positive', 'N/A')}")
                                st.warning(f"⚠️ Note: {hotel['guest_reviews'].get('negative', 'N/A')}")
                            
                            st.markdown(f"**Check-in:** {hotel.get('check_in_time', 'N/A')}")
                            st.markdown(f"**Check-out:** {hotel.get('check_out_time', 'N/A')}")
                            st.markdown(f"**Cancellation:** {hotel.get('cancellation_policy', 'N/A')}")
            
            # Mid-Range Hotels
            with midrange_tab:
                st.markdown("### Mid-Range Hotels")
                for hotel in hotels_data.get('midrange_hotels', []):
                    with st.expander(f"⭐ {hotel.get('name', 'Hotel')} ★{hotel.get('stars', 4)} ({hotel.get('nightly_rate', 'N/A')})"):
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.markdown(f"**Rating:** ⭐ {hotel.get('rating', 'N/A')} ({hotel.get('review_count', 0)} reviews)")
                            st.markdown(f"**Introduction:**\n{hotel.get('introduction', hotel.get('description', 'No description available'))}")
                            
                            if hotel.get('highlights'):
                                st.markdown("**Highlights:**")
                                for highlight in hotel.get('highlights', []):
                                    st.markdown(f"- {highlight}")
                        
                        with col2:
                            # Display hotel images
                            images = fetch_hotel_images(
                                hotel.get('name', 'Hotel'),
                                hotels_data.get('city', ''),
                                per_page=2
                            )
                            if images:
                                img_cols = st.columns(len(images))
                                for idx, img in enumerate(images):
                                    with img_cols[idx]:
                                        try:
                                            st.image(img['url'], use_container_width=True)
                                            st.caption("🏨 Hotel photo")
                                        except:
                                            st.info("Image unavailable")
                        
                        with st.expander("📋 Full Details"):
                            st.markdown("**Amenities:**")
                            amenities = hotel.get('amenities', [])
                            cols_amenities = st.columns(2)
                            for idx, amenity in enumerate(amenities):
                                with cols_amenities[idx % 2]:
                                    st.markdown(f"✓ {amenity}")
            
            # Luxury Hotels
            with luxury_tab:
                st.markdown("### Luxury Hotels")
                for hotel in hotels_data.get('luxury_hotels', []):
                    with st.expander(f"👑 {hotel.get('name', 'Hotel')} ★{hotel.get('stars', 5)} ({hotel.get('nightly_rate', 'N/A')})"):
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.markdown(f"**Rating:** ⭐ {hotel.get('rating', 'N/A')} ({hotel.get('review_count', 0)} reviews)")
                            st.markdown(f"**Introduction:**\n{hotel.get('introduction', hotel.get('description', 'No description available'))}")
                            
                            if hotel.get('highlights'):
                                st.markdown("**Highlights:**")
                                for highlight in hotel.get('highlights', []):
                                    st.markdown(f"- {highlight}")
                        
                        with col2:
                            # Display hotel images
                            images = fetch_hotel_images(
                                hotel.get('name', 'Hotel'),
                                hotels_data.get('city', ''),
                                per_page=2
                            )
                            if images:
                                img_cols = st.columns(len(images))
                                for idx, img in enumerate(images):
                                    with img_cols[idx]:
                                        try:
                                            st.image(img['url'], use_container_width=True)
                                            st.caption("🏨 Hotel photo")
                                        except:
                                            st.info("Image unavailable")
                        
                        with st.expander("📋 Full Details"):
                            st.markdown("**Amenities:**")
                            amenities = hotel.get('amenities', [])
                            cols_amenities = st.columns(2)
                            for idx, amenity in enumerate(amenities):
                                with cols_amenities[idx % 2]:
                                    st.markdown(f"✓ {amenity}")
    
    st.divider()
    st.subheader("🎯 Generate Your Itinerary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📝 Generate Detailed Itinerary", type="primary", use_container_width=True, key="generate_itinerary"):
            if not st.session_state.plan_data["destination"]:
                st.error("❌ Please select a destination")
            elif not st.session_state.plan_data["preferences"]:
                st.error("❌ Please select your travel preferences")
            else:
                with st.spinner("Generating your personalized itinerary..."):
                    days = (st.session_state.plan_data["end_date"] - st.session_state.plan_data["start_date"]).days + 1
                    
                    itinerary = generate_itinerary(
                        days=days,
                        attractions=st.session_state.plan_data.get("selected_attractions", []),
                        budget=st.session_state.plan_data["budget"],
                        preferences=st.session_state.plan_data["preferences"],
                        api_key=api_key_input
                    )
                    
                    st.session_state.generated_itinerary = itinerary
                    st.success("✅ Itinerary generated!")
    
    with col2:
        if "generated_itinerary" in st.session_state:
            if st.button("📋 View & Share Plan", type="secondary", use_container_width=True, key="go_to_get_plan"):
                st.session_state.current_page = "get_plan"
                st.rerun()
    
    # Display generated itinerary
    if "generated_itinerary" in st.session_state:
        st.markdown("### Your Perfect Itinerary")
        
        st.divider()
        
        # Display itinerary as table instead of markdown
        display_itinerary_as_table(st.session_state.generated_itinerary)
        
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 Download as Excel", use_container_width=True, key="download_excel"):
                excel_data = create_excel_export(
                    st.session_state.plan_data,
                    st.session_state.generated_itinerary
                )
                
                if excel_data:
                    st.download_button(
                        label="⬇️ Download Excel File",
                        data=excel_data,
                        file_name=f"travel_plan_{st.session_state.plan_data['destination']}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
        
        with col2:
            email = st.text_input(
                "📧 Email Address",
                placeholder="your.email@example.com",
                key="email_input"
            )
            
            if st.button("✉️ Send to Email", use_container_width=True, key="send_email_btn"):
                if email and "@" in email:
                    # Get Excel attachment
                    excel_data = create_excel_export(
                        st.session_state.plan_data,
                        st.session_state.generated_itinerary
                    )
                    
                    # Send email
                    success, message = send_email(
                        email,
                        f"Your {st.session_state.plan_data['destination']} Travel Plan",
                        st.session_state.generated_itinerary,
                        excel_data
                    )
                    
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.error("❌ Please enter a valid email address")


# =============================================================================
# World Map Selector - Select Country Page
# =============================================================================

def render_map_selector(available_countries: List[str], cover_picture_path: Path):
    """Render interactive world map for country selection."""
    if not HAS_FOLIUM:
        st.error("Folium library not installed. Please install: pip install folium streamlit-folium")
        return None
    
    # Country coordinates
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
    
    # Create map
    m = folium.Map(location=[20, 0], zoom_start=3, tiles="OpenStreetMap")
    
    # Add markers for countries
    for country, (lat, lon) in COUNTRY_COORDS.items():
        if country in available_countries:
            # Green marker for available countries
            folium.CircleMarker(
                location=[lat, lon],
                radius=12,
                popup=f"<b>{country}</b><br>✅ Available",
                color='#22c55e',
                fill=True,
                fillColor='#22c55e',
                fillOpacity=0.8,
                weight=2
            ).add_to(m)
        else:
            # Gray marker for unavailable countries
            folium.CircleMarker(
                location=[lat, lon],
                radius=10,
                popup=f"{country}<br>⚪ No data",
                color='#9ca3af',
                fill=True,
                fillColor='#d1d5db',
                fillOpacity=0.5,
                weight=1
            ).add_to(m)
    
    # Render map and get selection
    map_data = st_folium(m, width=1200, height=600)
    
    # Check if marker was clicked
    selected_country = None
    if map_data and map_data.get('last_clicked'):
        clicked_lat = map_data['last_clicked']['lat']
        clicked_lng = map_data['last_clicked']['lng']
        
        # Find closest country
        min_dist = float('inf')
        for country, (lat, lon) in COUNTRY_COORDS.items():
            dist = ((lat - clicked_lat)**2 + (lon - clicked_lng)**2)**0.5
            if dist < min_dist and country in available_countries:
                min_dist = dist
                selected_country = country
    
    return selected_country


def render_country_selector_page(available_countries: List[str], cover_picture_path: Path):
    """Render the country selection page with map."""
    display_top_banner("🌍 Select Your Destination")
    st.caption("Click on a green marker to select a country")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("World Map - Available Destinations")
        selected_country = render_map_selector(available_countries, cover_picture_path)
        
        if selected_country:
            st.session_state.selected_country = selected_country
    
    with col2:
        st.subheader("Quick Select")
        
        # Dropdown selector as backup
        selected = st.selectbox(
            "Or choose a country:",
            available_countries,
            index=0,
            label_visibility="collapsed"
        )
        
        # Display book cover if available
        if selected:
            cover_path = cover_image_path(cover_picture_path, selected)
            if cover_path is not None:
                st.image(str(cover_path), use_container_width=True)
                st.caption(f"📖 **{selected}**")
            
            if st.button("I want to go there! ✈️", use_container_width=True, key="go_to_city"):
                st.session_state.selected_country = selected
                st.session_state.current_page = "city_select"
                st.rerun()


def render_city_selector_page(available_countries: List[str], api_key_input: str):
    """Render the city selection page with weather and attractions."""
    display_top_banner("🏙️ Select Your City")
    
    country = st.session_state.get("selected_country")
    if not country:
        st.error("Please select a country first")
        if st.button("← Back to Country Selection", key="back_to_country"):
            st.session_state.current_page = "country_select"
            st.rerun()
        st.stop()
    
    st.subheader(f"Top Cities in {country}")
    
    # Get top cities
    if st.button("🔍 Get Top Cities", use_container_width=True, key="get_cities"):
        with st.spinner(f"Finding top cities in {country}..."):
            try:
                client = AzureOpenAI(
                    api_key=api_key_input,
                    api_version="2024-10-21",
                    azure_endpoint=AZURE_ENDPOINT,
                )
                
                prompt = f"""Generate top 5 tourist cities in {country}.
For each city, provide:
- name: City name
- description: Brief 1-line description
- best_for: What the city is famous for

Return as JSON array only with these exact fields."""
                
                response = client.chat.completions.create(
                    model=AZURE_DEPLOYMENT_NAME,
                    messages=[
                        {"role": "system", "content": "You are a travel expert. Return only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                response_text = response.choices[0].message.content
                import json as json_module
                
                # Try to extract JSON
                try:
                    cities = json_module.loads(response_text)
                except:
                    import re
                    json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                    if json_match:
                        cities = json_module.loads(json_match.group())
                    else:
                        cities = []
                
                if cities:
                    st.session_state.cities = cities
                else:
                    st.warning("Could not fetch cities. Please try again.")
            
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Display cities
    if "cities" in st.session_state:
        cities = st.session_state.cities
        
        for idx, city in enumerate(cities):
            with st.container(border=True):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"### {city.get('name', 'City')}")
                    st.write(city.get('description', 'No description'))
                    st.caption(f"🏆 **Best for:** {city.get('best_for', 'N/A')}")
                
                with col2:
                    if st.button(f"Select {city.get('name', 'City')} →", 
                                use_container_width=True, 
                                key=f"select_city_{idx}"):
                        st.session_state.selected_city = city.get('name', f"City {idx+1}")
                        st.session_state.current_page = "plan"
                        st.rerun()
    
    if st.button("← Back to Country Selection", key="back_from_city"):
        st.session_state.current_page = "country_select"
        st.rerun()


# =============================================================================
# Splash screen with video and tagline
# =============================================================================

def render_splash():
    """Show splash screen with video animation for 3 seconds."""
    animation_path = _BASE_DIR / "Animation rotate.webm"
    
    # CSS for video display (no rotation)
    splash_css = """
    <style>
        .splash-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 60px 20px;
        }
        
        .splash-video {
            display: inline-block;
            margin-bottom: 30px;
        }
        
        .splash-title {
            font-size: 36px;
            font-weight: bold;
            color: #1f77f2;
            margin-bottom: 20px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .splash-tagline {
            font-size: 22px;
            color: #595959;
            margin-bottom: 16px;
            font-weight: 500;
        }
        
        .splash-subtitle {
            font-size: 14px;
            color: #888888;
        }
    </style>
    """
    
    splash_html = splash_css + '<div class="splash-container">'
    
    if animation_path.exists():
        with open(animation_path, "rb") as f:
            vid_b64 = base64.b64encode(f.read()).decode()
        splash_html += (
            f'<video autoplay muted playsinline class="splash-video" style="width:150px; height:150px; '
            f'object-fit:contain;">'
            f'<source src="data:video/webm;base64,{vid_b64}" type="video/webm"></video>'
        )
    
    splash_html += """
        <div class="splash-title">Your Loved Lonely Planet</div>
        <div class="splash-tagline">Jobs fill your pocket, but adventures fill your soul.</div>
        <div class="splash-subtitle">Intelligent Travel Guide & Semantic Search · Group 7</div>
    </div>"""
    
    st.markdown(splash_html, unsafe_allow_html=True)
    time.sleep(3)  # 3 seconds splash screen
    st.session_state.splash_done = True
    st.rerun()


# =============================================================================
# Main app entry
# =============================================================================



def main():
    """Main application flow: sidebar, layout, search, and results."""
    if "splash_done" not in st.session_state:
        st.session_state.splash_done = False
    
    if "current_page" not in st.session_state:
        st.session_state.current_page = "search"  # "search", "plan", or "get_plan"

    if not st.session_state.splash_done:
        render_splash()
        return

    if not DATA_DIR.exists():
        st.error("No knowledge bases found.")
        st.stop()

    available_countries = sorted(
        [f.stem for f in DATA_DIR.iterdir() if f.suffix == ".pkl"]
    )
    if not available_countries:
        st.error("No knowledge bases found.")
        st.stop()

    cover_picture_path = _BASE_DIR / "cover_picture"

    with st.sidebar:
        st.markdown("## 🧭 Navigation")
        
        # Determine current radio index based on page
        page_options = ["🌍 Select Country", "🏙️ Select City", "🔍 Smart Search", "✈️ Create Plan", "📋 Get Your Plan"]
        current_index = 0
        
        if st.session_state.current_page == "country_select":
            current_index = 0
        elif st.session_state.current_page == "city_select":
            current_index = 1
        elif st.session_state.current_page == "search":
            current_index = 2
        elif st.session_state.current_page == "plan":
            current_index = 3
        elif st.session_state.current_page == "get_plan":
            current_index = 4
        
        page = st.radio(
            "Choose Mode:",
            page_options,
            index=current_index,
            key="page_selector"
        )
        
        # Update current_page based on radio selection
        if "Select Country" in page:
            st.session_state.current_page = "country_select"
        elif "Select City" in page:
            st.session_state.current_page = "city_select"
        elif "Search" in page:
            st.session_state.current_page = "search"
        elif "Create Plan" in page:
            st.session_state.current_page = "plan"
        elif "Get Your Plan" in page:
            st.session_state.current_page = "get_plan"
        
        st.divider()
        
        search_top_k, use_llm, api_key_input, show_debug = render_sidebar(
            available_countries, cover_picture_path
        )

    # Initialize current_page if not set
    if "current_page" not in st.session_state:
        st.session_state.current_page = "search"
    
    # PAGE 1: Select Country with World Map
    if st.session_state.current_page == "country_select":
        render_country_selector_page(available_countries, cover_picture_path)
    
    # PAGE 2: Select City with Weather and Attractions
    elif st.session_state.current_page == "city_select":
        render_city_selector_page(available_countries, api_key_input)
    
    # PAGE 3: Smart Search
    elif st.session_state.current_page == "search":
        display_top_banner("Your Loved Lonely Planet Travel Guide")
        st.caption("Fast Semantic Search + AI-Powered Recommendations by Azure OpenAI")

        col1, col2 = st.columns([1, 3], gap="large")

        with col1:
            selected_country = render_destination_panel(
                available_countries, cover_picture_path
            )
            # Save to session state for plan page
            st.session_state.selected_country = selected_country

        with col2:
            st.subheader("Step2. Type Your Travel Questions")
            query = st.text_area(
                "Ask about your destination:",
                placeholder=(
                    "Examples:\n"
                    "What are the best attractions?\n"
                    "Local food recommendations?\n"
                    "Best time to visit?\n"
                    "Budget travel tips?"
                ),
                height=100,
                label_visibility="collapsed",
            )
            
            col_search, col_plan = st.columns(2)
            with col_search:
                search_clicked = st.button("Step3. Search & Analyze", type="primary", use_container_width=True, key="search_btn")
            
            with col_plan:
                plan_clicked = st.button("Let's make a travel plan ✈️", use_container_width=True, key="plan_btn")
            
            if plan_clicked:
                st.session_state.current_page = "plan"
                st.rerun()

            if search_clicked and query and selected_country:
                with st.spinner("Searching knowledge base..."):
                    results, scores = semantic_search(
                        query, selected_country, top_k=search_top_k
                    )

                    if not results:
                        st.error("No relevant content found.")
                    else:
                        keywords = extract_keywords([r["text"] for r in results])
                        render_search_results(
                            query,
                            selected_country,
                            results,
                            scores,
                            keywords,
                            use_llm,
                            api_key_input,
                            search_top_k,
                            show_debug,
                        )

            elif search_clicked and not query:
                st.warning("Hey please enter a question:)")
            elif search_clicked and not selected_country:
                st.warning("Hey please select a destination:)")
    
    # PAGE 4: Travel Plan Creator
    elif st.session_state.current_page == "plan":
        render_travel_plan_page(available_countries, api_key_input)
    
    # PAGE 5: Get Your Plan (View & Share)
    elif st.session_state.current_page == "get_plan":
        render_get_plan_page()


if __name__ == "__main__":
    main()
