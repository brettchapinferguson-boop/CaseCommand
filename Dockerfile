FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .
COPY index.html .

EXPOSE 3000

ENV PORT=3000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3000"]
