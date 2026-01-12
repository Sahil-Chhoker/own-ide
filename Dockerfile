FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install dependencies first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy the rest of your code
COPY . .

# 3. Run the app
# Use '0.0.0.0' so the container is accessible from outside
CMD ["fastapi", "run", "main.py", "--port", "8000", "--host", "0.0.0.0", "--workers", "1"]