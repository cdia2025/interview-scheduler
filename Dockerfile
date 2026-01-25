# Use modern Python
FROM python:3.11-slim

WORKDIR /app

# Install system deps (for reportlab/Pillow)
RUN apt-get update && apt-get install -y \
    gcc libfreetype6-dev libjpeg62-turbo-dev libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port (Cloud Run provides PORT=8080)
EXPOSE 8080

# Launch with explicit host and port
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
