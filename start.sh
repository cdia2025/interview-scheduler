#!/bin/bash
set -e  # Exit on error

# Debug: print PORT
echo "🔧 Starting app with PORT=${PORT:-8080}"

# Launch Streamlit with explicit settings
exec streamlit run app.py \
    --server.port=${PORT:-8080} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false \
    --logger.level=debug
