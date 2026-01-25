# Use official Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system deps for reportlab/Pillow (optional but recommended)
RUN apt-get update && apt-get install -y \
    gcc \
    libfreetype6-dev \
    libjpeg62-turbo-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose port (Cloud Run expects $PORT)
EXPOSE 8080

# Run Streamlit on 0.0.0.0 and dynamic port
CMD ["sh", "-c", "streamlit run app.py --server.port=$PORT --server.address=0.0.0.0"]
