# Zeroc FastAPI Server
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py client.py ./

# Copy Zeroc implementation
COPY ../../implementations/python /app/implementations/python
RUN cd /app/implementations/python && pip install -e .

# Copy prototype (for protobuf schemas)
COPY ../../prototype /app/prototype

# Copy dictionaries
COPY ../../dictionaries /app/dictionaries

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run server
CMD ["python", "server.py"]
