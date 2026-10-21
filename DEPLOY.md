# Deploy

Two supported targets: **Streamlit Community Cloud** (public `.streamlit.app` URL,
free) and any **container host** that injects a `$PORT` (`start.sh`).

The repository is already prepared for both: no secrets are committed, assets are
web-optimised (≈133 MB total), and query embeddings run on `onnxruntime` (no
`torch`, so the build stays inside Streamlit Cloud's dependency budget).

> **Live app:** <https://yourloved-lonelyplanet-travelguide.streamlit.app>
> (public, custom subdomain; the default URL before the rename was
> `caseyxu2021-…-810f7s.streamlit.app`)

---

## 1. Streamlit Community Cloud (recommended)

1. Sign in at <https://share.streamlit.io> with the GitHub account that owns the
   repo (`CaseyXu2021/YourLovedLonleyPlanetTravelGuide`).
2. **New app** → **Deploy a public app from GitHub**.
3. Fill in:

   | Field | Value |
   |-------|-------|
   | Repository | `CaseyXu2021/YourLovedLonleyPlanetTravelGuide` |
   | Branch | `main` |
   | Main file path | `streamlit_app.py` |
   | Advanced settings → Python version | `3.11` or `3.12` |

4. **Advanced settings → Secrets** — paste (this is the only manual step, since
   keys are not in the repo):

   ```toml
   AZURE_OPENAI_API_KEY = "<your key>"
   AZURE_OPENAI_ENDPOINT = "https://hkust.azure-api.net"
   AZURE_OPENAI_DEPLOYMENT = "gpt-4o-mini"
   AZURE_OPENAI_API_VERSION = "2024-10-21"
   OUTSCRAPER_API_KEY = "<optional>"
   UNSPLASH_ACCESS_KEY = "<optional>"
   ```

5. **Deploy**. First build takes 4–8 minutes (installing `onnxruntime`,
   `streamlit-folium`, `python-docx`). The URL will look like
   `https://<app-name>.streamlit.app`.

Cold start after 7 days of inactivity: ~30 s, then instant.

---

## 2. Container / PaaS host

```bash
export PORT=8501
bash start.sh
```

`start.sh` binds `0.0.0.0:$PORT`, disables the file watcher and CORS, and runs
`streamlit_app.py`. Provide secrets either as environment variables
(`AZURE_OPENAI_API_KEY=…`) or by shipping `.streamlit/secrets.toml` with the
image.

To build a lean deploy bundle (JPEG-downscaled imagery, INT8 model, no caches):

```bash
python prepare_deploy.py     # writes .deploy_build/
```

---

## 3. Local run

```bash
pip install -r requirements.txt
cp .streamlit/secrets.example.toml .streamlit/secrets.toml   # fill in the key
streamlit run streamlit_app.py
```

---

## Notes

- `.streamlit/secrets.toml` is git-ignored; `settings.py` reads env vars first,
  then Streamlit secrets, then falls back to empty values so the app never
  crashes on a missing key (it degrades to retrieval-only answers).
- `knowledge_bases/*.pkl`, `models/`, `book_picture/` and `cover_picture/` are
  committed on purpose — the app is self-contained and needs no external storage.
- Streamlit Cloud rebuilds on every push to `main`. Rebooting after a secrets
  change is required for the new values to take effect.
