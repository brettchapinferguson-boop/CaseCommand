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

# Copy frontend into static directory (multiple fallback locations)
RUN mkdir -p static
COPY frontend/index.html static/index.html

# Also copy to /app root just in case
COPY frontend/index.html /app/index.html

# Verify the file exists
RUN echo "=== Verifying frontend files ===" && \
    ls -la static/index.html && \
    wc -c static/index.html && \
    echo "=== Frontend ready ==="

# Expose port
EXPOSE 8000

# Run server
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}
