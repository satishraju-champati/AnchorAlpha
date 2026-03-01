# AnchorAlpha Streamlit Application Dockerfile
# Optimized for AWS Lightsail deployment

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and curl for health checks
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# Copy the application code
COPY src/ ./src/
COPY cfg/ ./cfg/

# Set Python path and environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_FILE_WATCHER_TYPE=none
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 app && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Create Streamlit config directory
RUN mkdir -p /home/app/.streamlit

# Create Streamlit configuration
RUN echo '[server]\n\
headless = true\n\
port = 8501\n\
address = "0.0.0.0"\n\
fileWatcherType = "none"\n\
\n\
[browser]\n\
gatherUsageStats = false\n\
\n\
[theme]\n\
base = "dark"\n\
primaryColor = "#FFD700"\n\
backgroundColor = "#001f3f"\n\
secondaryBackgroundColor = "#2c3e50"\n\
textColor = "#ffffff"\n' > /home/app/.streamlit/config.toml

# Expose Streamlit port
EXPOSE 8501

# Health check with proper curl options
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f --connect-timeout 5 --max-time 10 http://localhost:8501/_stcore/health || exit 1

# Run Streamlit app with optimized settings
CMD ["streamlit", "run", "src/AnchorAlpha/streamlit_app/momentum_dashboard.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.fileWatcherType=none", \
     "--browser.gatherUsageStats=false", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false"]