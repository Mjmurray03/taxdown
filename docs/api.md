# Taxdown API Reference

Base URL: `http://localhost:8000/api/v1`

## Authentication

Include API key in header:

```
X-API-Key: your-api-key
```

## Endpoints

### Properties

#### Search Properties

`POST /properties/search`

Request:

```json
{
  "query": "123 Main St",
  "city": "Bella Vista",
  "min_value": 100000,
  "max_value": 500000,
  "page": 1,
  "page_size": 20
}
```

#### Get Property

`GET /properties/{id}`

### Analysis

#### Analyze Property

`POST /analysis/assess`

Request:

```json
{
  "property_id": "uuid",
  "include_comparables": true
}
```

Response:

```json
{
  "status": "success",
  "data": {
    "fairness_score": 72,
    "confidence_level": 85,
    "recommended_action": "APPEAL",
    "estimated_savings": 450.00
  }
}
```

### Appeals

#### Generate Appeal

`POST /appeals/generate`

Request:

```json
{
  "property_id": "uuid",
  "style": "formal"
}
```

#### Download PDF

`POST /appeals/generate/{property_id}/pdf`

### Portfolios

#### Create Portfolio

`POST /portfolios?user_id={user_id}`

#### Get Dashboard

`GET /portfolios/{portfolio_id}/dashboard`
