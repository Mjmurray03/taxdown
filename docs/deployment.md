# Deployment Guide

## Production Checklist

- [ ] Set `TAXDOWN_DEBUG=false`
- [ ] Configure production database URL
- [ ] Set up API key authentication
- [ ] Configure rate limiting
- [ ] Set up SSL/TLS
- [ ] Configure CORS for production domain
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy

## Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Environment Configuration

Production `.env`:

```
DATABASE_URL=postgresql://user:pass@db.example.com:5432/taxdown
TAXDOWN_DEBUG=false
TAXDOWN_REQUIRE_API_KEY=true
TAXDOWN_API_KEYS=key1,key2,key3
TAXDOWN_CORS_ORIGINS=https://app.taxdown.com
```
