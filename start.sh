#!/usr/bin/env bash
# Start the Streamlit app on the port injected by the hosting platform.
set -euo pipefail
PORT="${PORT:-8501}"
exec streamlit run streamlit_app.py \
  --server.port "$PORT" \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false \
  --server.fileWatcherType none
