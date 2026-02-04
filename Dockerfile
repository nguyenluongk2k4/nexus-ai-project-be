FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Pre-download AI models
# Using the model name from settings.py: sentence-transformers/paraphrase-multilingual-mpnet-base-v2
RUN --mount=type=cache,target=/root/.cache/huggingface \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')"

# Copy backend source
COPY . .

# Expose port (FastAPI default)
EXPOSE 8000

# Entrypoint
CMD ["python", "-m", "app.main"]
