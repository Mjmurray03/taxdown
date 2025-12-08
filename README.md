# Taxdown - Property Tax Intelligence Platform

AI-powered property tax assessment analysis for Bella Vista, AR.

## Features

- **Property Search**: Search 150,000+ Benton County properties
- **Assessment Analysis**: AI compares your property to similar ones
- **Appeal Generation**: Professional appeal letters with evidence
- **Portfolio Management**: Track multiple properties
- **Savings Calculator**: Estimate potential tax savings

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Node.js 18+

### Backend Setup

```bash
# Clone repository
git clone https://github.com/your-org/taxdown.git
cd taxdown

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set up database
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
alembic upgrade head

# Start API server
uvicorn src.api.main:app --reload
```

### Frontend Setup

```bash
cd dashboard
npm install
npm run dev
```

### Load Sample Data

```bash
python scripts/load_assessor_data.py --file data/assessor_export.csv
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
taxdown/
├── src/
│   ├── api/              # FastAPI application
│   ├── models/           # SQLAlchemy models
│   ├── services/         # Business logic
│   └── etl/              # Data pipeline
├── dashboard/            # Next.js frontend
├── tests/                # Test suite
├── scripts/              # Utility scripts
└── docs/                 # Documentation
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | - |
| TAXDOWN_DEBUG | Enable debug mode | false |
| TAXDOWN_API_KEY | API key for authentication | - |

## License

Proprietary - All rights reserved
