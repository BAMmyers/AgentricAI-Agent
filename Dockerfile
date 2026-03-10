# Dockerfile for AgentricAI API
FROM python:3.14-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Environment defaults
ENV AGENTRIC_HOST=0.0.0.0
ENV AGENTRIC_API_PORT=3939
ENV AGENTRIC_OLLAMA_URL=http://ollama:11434

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3939/health').read()"

# Run server
CMD ["python", "main.py"]