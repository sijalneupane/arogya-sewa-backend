# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies: Git + build tools (if needed for packages like psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code, 
COPY . .
# we can also use entry point
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
# Production Dockerfile below (commented out for reference)
# FROM python:3.11-slim

# # Set working directory
# WORKDIR /app

# # Install system dependencies
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     git curl \
#     && rm -rf /var/lib/apt/lists/*

# # Copy requirements first for caching
# COPY requirements.txt .

# # Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy your app code
# COPY . .

# # Default command (for production, override in devcontainer if needed)
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
