FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY cfg/ cfg/

# Add src to Python path so AnchorAlpha package is importable
ENV PYTHONPATH=/app/src

CMD ["python", "-m", "AnchorAlpha.trading.trading_engine"]
