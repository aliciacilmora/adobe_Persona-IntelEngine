# --- Stage 1: Builder ---
FROM python:3.9.18-slim-bullseye as builder

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==1.13.1 \
    -r requirements.txt

# ✅ Save the model locally so it can be reused in the final image
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
model = SentenceTransformer('all-MiniLM-L6-v2'); \
model.save('/app/model')"


# --- Stage 2: Final Runtime Image ---
FROM python:3.9.18-slim-bullseye

WORKDIR /app

# Copy Python packages
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages

# ✅ Copy the pre-saved model
COPY --from=builder /app/model /app/model

# Optional: If you really want to preserve Hugging Face cache as well:
# COPY --from=builder /root/.cache /root/.cache

# Copy your Python application
COPY parser.py .

# ✅ Offline-safe model loading path
ENV MODEL_PATH=/app/model

# Run the app
CMD ["python", "parser.py"]
