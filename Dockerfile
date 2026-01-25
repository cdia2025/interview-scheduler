# Use official Python 3.11 slim base image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies required by Pillow, ReportLab, etc.
# Non-interactive mode to avoid prompts during build
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libfreetype6-dev \
        libjpeg62-turbo-dev \
        libpng-dev \
        && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .
# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code (including .ttf font if present)
COPY . .

# Make startup script executable
RUN chmod +x ./start.sh

# Expose port (documentation only; Cloud Run sets $PORT at runtime)
EXPOSE $PORT

# Start the app using the shell script to ensure $PORT expansion and signal handling
ENTRYPOINT ["./start.sh"]
