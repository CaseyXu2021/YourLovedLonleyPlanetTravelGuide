# Your Loved Lonely Planet — Intelligent Travel Guide

Semantic search over Lonely Planet guidebooks, plus an AI travel-plan builder
(destination → city → attractions → itinerary → Excel/Word export).

**Group 7:** Casey · Jasper · Maxine · Paew

---

## What it does

1. **Search** — ask a natural-language question about a destination; the app
   retrieves the top-5 most relevant guide passages (cosine similarity over
   `all-MiniLM-L6-v2` embeddings) and asks Azure OpenAI `gpt-4o-mini` to answer
   with citations back to the source pages.
2. **Plan** — pick a country → city → travel dates and preferences → the app
   suggests attractions, hotels and restaurants (LLM-generated, cached) →
   generate a day-by-day itinerary → export to Excel / Word.

## Architecture

| Layer | Choice | Why |
|-------|--------|-----|
| UI | Streamlit | fastest path to a shareable data app |
| Retrieval | Pre-computed MiniLM embeddings in `knowledge_bases/*.pkl` | no GPU, instant cold start |
| Query embedding | `onnxruntime` + `tokenizers` running `models/all-MiniLM-L6-v2/model.onnx` (INT8) | no `torch` / `sentence-transformers` (~2 GB saved), identical vectors |
| Generation | Azure OpenAI `gpt-4o-mini` via HKUST gateway | course-provided endpoint |
| Export | `openpyxl`, `python-docx` | no extra services |

`embedding_backend.py` reproduces `SentenceTransformer.encode()` exactly:
mean-pooled, L2-normalised, with `attention_mask` weighting — cosine similarity
against the stored KB vectors is 1.0000.

## Project layout

```
app_simplified_original.py   main app (pages: splash, search, plan, get_plan)
streamlit_app.py             entry point for Streamlit Cloud
embedding_backend.py         ONNX query encoder (lazy-loaded, cached)
settings.py                  secret resolution (env -> st.secrets)
attractions_service.py       LLM attraction suggestions per city
city_selector.py             country -> city selection UI
hotels_service.py            LLM hotel suggestions
restaurants_service.py       LLM restaurant suggestions
travel_plan_designer.py      itinerary generation
image_service.py             attraction/Google image lookup + fallbacks
hotel_pictures_service.py    hotel photo lookup + fallbacks
knowledge_bases/             one pickle per destination (chunks + embeddings)
models/all-MiniLM-L6-v2/     ONNX model + tokenizer (INT8, 22.9 MB)
book_picture/, cover_picture/  destination imagery (web-optimised)
prepare_deploy.py            builds a trimmed .deploy_build/ package
start.sh                     port-injecting launcher for container hosts
```

## Run locally

```bash
pip install -r requirements.txt
cp .streamlit/secrets.example.toml .streamlit/secrets.toml   # then fill in keys
streamlit run streamlit_app.py
```

Open http://localhost:8501.

## Configuration

No keys are committed. `settings.py` resolves each key from, in order:

1. the environment variable (e.g. `AZURE_OPENAI_API_KEY`), then
2. Streamlit secrets (`.streamlit/secrets.toml`, git-ignored).

| Key | Required | Purpose |
|-----|----------|---------|
| `AZURE_OPENAI_API_KEY` | yes | LLM answers and plan generation |
| `AZURE_OPENAI_ENDPOINT` | yes | default `https://hkust.azure-api.net` |
| `AZURE_OPENAI_DEPLOYMENT` | no | default `gpt-4o-mini` |
| `OUTSCRAPER_API_KEY` | no | attraction / hotel photos; falls back to generic imagery |
| `UNSPLASH_ACCESS_KEY` | no | fallback photo source |

Without a valid Azure key the app still runs: search returns the retrieved
guide passages without an AI summary, and plan generation is disabled.

## Deploy

See [DEPLOY.md](DEPLOY.md) — Streamlit Community Cloud, plus a container
recipe (`start.sh` honours the platform-injected `$PORT`).

## Data / credits

Guide text and imagery are derived from Lonely Planet guidebooks for a course
project; not for redistribution.
