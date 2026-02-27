FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for PyMuPDF and cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy frontend into static directory
RUN mkdir -p static
COPY frontend/index.html static/index.html

# Expose port
EXPOSE 8000

# Run server - use shell form so $PORT env var is expanded at runtime
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}
