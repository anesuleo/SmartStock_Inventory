FROM python:3.11-slim AS builder

WORKDIR /app

# Ensure system is up to date and pip is modern
RUN pip install --upgrade pip wheel

# Install requirements into wheelhouse
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Runtime image
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create non-root user
RUN useradd -m appuser

# Install wheels (fast, repeatable, lightweight)
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application source code
COPY . .

# Ensure appuser owns application files
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 8000

# FastAPI startup command
CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port=8000"]
