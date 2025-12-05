FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p instance uploads/resumes uploads/icons

# Expose port
EXPOSE 8181

# Run migrations and start app
# Run migrations (both Flask-Migrate and manual script) and start app
CMD python migrate_db.py && flask db upgrade 2>/dev/null || true && python -m app

