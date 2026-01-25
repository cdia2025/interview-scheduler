FROM python:3.11-slim

WORKDIR /app

# Install system deps for Pillow, ReportLab, etc.
RUN apt-get update && apt-get install -y \
    gcc \
    libfreetype6-dev \
    libjpeg62-turbo-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE $PORT

# Use shell form to expand $PORT
CMD streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
