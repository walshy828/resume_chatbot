FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user first
RUN useradd -m -u 1000 appuser

# Create necessary directories and set ownership
WORKDIR /app
RUN mkdir -p /app/instance /app/uploads/resumes /app/uploads/icons /app/logs \
    && chown -R appuser:appuser /app

# Copy application and set ownership
COPY --chown=appuser:appuser . .

# Expose port
EXPOSE 8181

# Run migrations and start app
COPY --chown=appuser:appuser entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER appuser

ENTRYPOINT ["/entrypoint.sh"]
