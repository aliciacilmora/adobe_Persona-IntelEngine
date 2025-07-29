FROM python:3.9.18-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install torch first, using the CPU wheel index
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu torch==2.1.0

# Install other Python dependencies
RUN pip install -r requirements.txt

# Copy model (already downloaded) and app code
COPY model_cache /app/model
COPY parser.py .

# Tell the app where to find the model
ENV MODEL_PATH=/app/model

# Run the parser
CMD ["python", "parser.py"]
