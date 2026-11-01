FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.txt

# Keep the session tokenizer in the image so first writes and recreated
# containers do not need to download runtime assets.
ENV TIKTOKEN_CACHE_DIR=/opt/remembr/tiktoken
RUN python -c "import functools, requests, tiktoken; requests.get = functools.partial(requests.get, timeout=60); tiktoken.get_encoding('cl100k_base')"

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Start the server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
