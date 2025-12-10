# Taxdown - Property Tax Intelligence Platform

An AI-powered property tax assessment analysis platform for Northwest Arkansas, starting with Benton County. Taxdown helps property owners and investors identify over-assessed properties, generate professional appeal letters, and manage property portfolios.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [Database Setup](#database-setup)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Development](#development)
- [License](#license)

## Overview

Taxdown analyzes property tax assessments using a sales comparison approach, comparing target properties against similar properties in the same area. The platform calculates fairness scores, estimates potential tax savings, and generates ready-to-file appeal letters with supporting evidence.

### Target Market

- **Primary**: Real estate investors with multiple properties
- **Secondary**: Real estate agents, individual homeowners
- **Geographic Focus**: Benton County, Arkansas (173,000+ parcels)

## Features

### Property Search and Analysis
- Search 173,000+ Benton County properties by address, parcel ID, owner name, or subdivision
- Filter by value range, property type, and assessment category
- View detailed property information including valuations, owner data, and characteristics

### Assessment Fairness Analysis
- Automated fairness scoring (0-100 scale) using comparable property analysis
- Statistical comparison against neighborhood and subdivision averages
- Confidence scoring based on comparable property availability
- Identification of appeal candidates based on over-assessment indicators

### Appeal Letter Generation
- Professional appeal letters in multiple styles (formal, detailed, concise)
- Executive summaries highlighting key arguments
- Evidence summaries with comparable property data
- PDF export with filing instructions and deadlines
- Arkansas Board of Equalization compliance

### Portfolio Management
- Create and manage property portfolios
- Track multiple properties across investments
- Aggregate savings potential across portfolios
- Dashboard with portfolio-wide analytics

### Reporting
- Assessment analysis reports
- Portfolio summary reports
- Comparative analysis exports

## Architecture

```
                           +------------------+
                           |   Next.js 16     |
                           |   Dashboard      |
                           |   (Vercel)       |
                           +--------+---------+
                                    |
                                    | HTTPS
                                    v
+------------------+       +------------------+       +------------------+
|   Cloudflare     | <---> |   FastAPI        | <---> |   PostgreSQL     |
|   (CDN/WAF)      |       |   Backend        |       |   + PostGIS      |
+------------------+       |   (Railway)      |       |   (Railway)      |
                           +--------+---------+       +------------------+
                                    |
                                    v
                           +------------------+
                           |   Claude API     |
                           |   (AI/ML)        |
                           +------------------+
```

### Core Services

| Service | Description |
|---------|-------------|
| AssessmentAnalyzer | Orchestrates property analysis workflow |
| ComparableService | Finds similar properties for comparison |
| FairnessScorer | Calculates statistical fairness scores |
| SavingsEstimator | Estimates potential tax savings |
| AppealGenerator | Generates appeal letters and packages |
| PortfolioService | Manages user property portfolios |

## Tech Stack

### Backend
- **Framework**: FastAPI 0.104+
- **Language**: Python 3.11+
- **Database**: PostgreSQL 15+ with PostGIS
- **ORM**: SQLAlchemy 2.0+
- **Validation**: Pydantic v2
- **AI**: Anthropic Claude API

### Frontend
- **Framework**: Next.js 16 (App Router)
- **Language**: TypeScript 5
- **UI Components**: Radix UI primitives
- **Styling**: Tailwind CSS 4
- **State Management**: TanStack Query
- **Charts**: Recharts

### Infrastructure
- **Backend Hosting**: Railway
- **Frontend Hosting**: Vercel
- **Database**: Railway PostgreSQL
- **Monitoring**: Sentry, Prometheus
- **Logging**: Structlog (JSON)

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- PostgreSQL 14+ with PostGIS extension
- Git

### Backend Setup

1. Clone the repository:
```bash
git clone https://github.com/your-org/taxdown.git
cd taxdown
```

2. Create and activate a virtual environment:
```bash
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Create environment configuration:
```bash
cp .env.example .env
```

5. Configure your `.env` file with database credentials and other settings.

6. Run database migrations:
```bash
python src/etl/run_migration.py
```

7. Start the API server:
```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Interactive documentation is at `/docs`.

### Frontend Setup

1. Navigate to the dashboard directory:
```bash
cd dashboard
```

2. Install Node.js dependencies:
```bash
npm install
```

3. Create local environment configuration:
```bash
cp .env.example .env.local
```

4. Start the development server:
```bash
npm run dev
```

The dashboard will be available at `http://localhost:3000`.

### Database Setup

The project uses PostgreSQL with PostGIS for spatial data. The schema includes:

- **properties**: Core property data (173,000+ records)
- **subdivisions**: Geographic subdivision boundaries
- **assessment_analyses**: Fairness analysis results
- **tax_appeals**: Generated appeal records
- **portfolios**: User portfolio management
- **users**: Authentication and profiles

To load property data:
```bash
python src/etl/load_properties.py --source data/parcels.shp
python src/etl/load_subdivisions.py --source data/subdivisions.shp
```

## Project Structure

```
taxdown/
├── src/
│   ├── api/                    # FastAPI application
│   │   ├── main.py            # Application entry point
│   │   ├── config.py          # Settings and configuration
│   │   ├── routes/            # API endpoint handlers
│   │   │   ├── properties.py  # Property search/details
│   │   │   ├── analysis.py    # Assessment analysis
│   │   │   ├── appeals.py     # Appeal generation
│   │   │   ├── portfolios.py  # Portfolio management
│   │   │   ├── reports.py     # Report generation
│   │   │   └── health.py      # Health checks
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── middleware/        # Request processing middleware
│   │   └── utils/             # API utilities
│   ├── services/              # Business logic layer
│   │   ├── assessment_analyzer.py
│   │   ├── comparable_service.py
│   │   ├── fairness_scorer.py
│   │   ├── savings_estimator.py
│   │   ├── appeal_generator.py
│   │   ├── appeal_models.py
│   │   ├── portfolio_service.py
│   │   └── pdf_generator.py
│   ├── etl/                   # Data pipeline scripts
│   │   ├── load_properties.py
│   │   ├── load_subdivisions.py
│   │   └── run_migration.py
│   └── config.py              # Database configuration
├── dashboard/                  # Next.js frontend
│   ├── src/
│   │   ├── app/               # App router pages
│   │   │   ├── page.tsx       # Dashboard home
│   │   │   ├── properties/    # Property pages
│   │   │   ├── appeals/       # Appeals management
│   │   │   ├── portfolio/     # Portfolio views
│   │   │   └── reports/       # Report generation
│   │   ├── components/        # React components
│   │   │   ├── ui/            # Base UI components
│   │   │   ├── layout/        # Layout components
│   │   │   └── ...
│   │   └── lib/               # Utilities and API client
│   │       ├── api.ts         # API client and types
│   │       ├── hooks.ts       # Custom React hooks
│   │       └── config.ts      # Frontend configuration
│   └── package.json
├── migrations/                 # SQL migration files
├── tests/                      # Test suite
├── docs/                       # Documentation
│   ├── api.md                 # API reference
│   └── deployment.md          # Deployment guide
├── scripts/                    # Utility scripts
├── requirements.txt           # Python dependencies
└── README.md
```

## API Reference

Base URL: `/api/v1`

### Properties

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/properties/search` | Search properties with filters |
| GET | `/properties/{id}` | Get property details |
| GET | `/properties/parcel/{parcel_id}` | Get property by parcel ID |

### Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analysis/analyze/{property_id}` | Run fairness analysis |
| GET | `/analysis/{property_id}` | Get existing analysis |

### Appeals

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/appeals/generate` | Generate appeal letter |
| POST | `/appeals/generate/{property_id}/pdf` | Download appeal as PDF |
| GET | `/appeals/list` | List generated appeals |
| GET | `/appeals/{appeal_id}` | Get appeal details |
| DELETE | `/appeals/{appeal_id}` | Delete an appeal |

### Portfolios

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/portfolios` | List user portfolios |
| POST | `/portfolios` | Create new portfolio |
| GET | `/portfolios/{id}` | Get portfolio details |
| POST | `/portfolios/{id}/properties` | Add property to portfolio |
| DELETE | `/portfolios/{id}/properties/{property_id}` | Remove property |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/ready` | Readiness check with DB status |

Full API documentation is available at `/docs` (Swagger UI) or `/redoc` (ReDoc).

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `TAXDOWN_DEBUG` | Enable debug mode (true/false) | No |
| `TAXDOWN_CORS_ORIGINS` | Comma-separated allowed origins | No |
| `ANTHROPIC_API_KEY` | Claude API key for AI features | No |
| `SENTRY_DSN` | Sentry error tracking DSN | No |
| `REDIS_URL` | Redis URL for caching | No |

### Fairness Scoring

The fairness score uses the following scale (from the taxpayer's perspective):

| Score | Interpretation | Recommendation |
|-------|----------------|----------------|
| 90-100 | Fairly assessed | No action needed |
| 70-89 | Slightly above comparables | Monitor |
| 50-69 | Moderately above comparables | Review recommended |
| 30-49 | Significantly over-assessed | Appeal candidate |
| 0-29 | Greatly over-assessed | Strong appeal candidate |

### Appeal Styles

| Style | Description |
|-------|-------------|
| `formal` | Professional legal tone for official submission |
| `detailed` | Comprehensive analysis with extensive evidence |
| `concise` | Brief key facts only |

## Deployment

### Production Checklist

- Set `TAXDOWN_DEBUG=false`
- Configure production database URL
- Set up API key authentication
- Configure rate limiting
- Enable SSL/TLS
- Configure CORS for production domain
- Set up monitoring (Sentry, Prometheus)
- Configure backup strategy

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY migrations/ migrations/

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Railway Deployment

The backend is configured for Railway deployment with automatic builds from the main branch.

### Vercel Deployment

The Next.js dashboard is configured for Vercel deployment with automatic preview deployments for pull requests.

## Development

### Running Tests

```bash
# Backend tests
pytest tests/ -v

# Frontend tests
cd dashboard && npm run test
```

### Code Quality

```bash
# Python linting
ruff check src/

# TypeScript linting
cd dashboard && npm run lint
```

### Database Migrations

```bash
# Run migrations
python src/etl/run_migration.py

# Create new migration
# Add SQL file to migrations/ with sequential numbering
```

## License

Proprietary - All rights reserved.

---

For questions or support, please open an issue on GitHub.
