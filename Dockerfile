FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .
COPY database.py .
COPY index.html .

# Create volume mount point for database persistence
VOLUME /app/data
ENV DATABASE_PATH=/app/data/casecommand.db

EXPOSE 3000

ENV PORT=3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:3000/api/health'); assert r.status_code == 200"

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3000", "--forwarded-allow-ips", "*"]
