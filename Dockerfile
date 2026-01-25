# Use official Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Pillow, ReportLab, etc.
RUN apt-get update && apt-get install -y \
    gcc \
    libfreetype6-dev \
    libjpeg62-turbo-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make startup script executable
RUN chmod +x ./start.sh

# Expose port (for documentation; Cloud Run sets $PORT)
EXPOSE $PORT

# Start app via shell script to ensure $PORT expansion and proper signal handling
ENTRYPOINT ["./start.sh"]
