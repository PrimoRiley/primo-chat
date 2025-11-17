FROM python:3.11-slim

# System packages only if you compile native extensions; otherwise omit
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Cloud Run injects $PORT; Chainlit defaults to 8000
CMD ["chainlit", "run", "app.py", "--host=0.0.0.0", "--port", "8000"]
