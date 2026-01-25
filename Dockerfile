# Use modern Python version
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for reportlab/Pillow (needed for PDF/Excel with fonts)
RUN apt-get update && apt-get install -y \
    gcc \
    libfreetype6-dev \
    libjpeg62-turbo-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (to leverage Docker cache)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (including font files like NotoSansCJKtc-Regular.ttf)
COPY . .

# Expose port (Cloud Run provides PORT=8080)
EXPOSE 8080

# Run Streamlit on all interfaces and dynamic port
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
