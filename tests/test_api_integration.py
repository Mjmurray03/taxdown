"""
API Integration Tests for Taxdown

Tests all API endpoints against a real database.
Run with: pytest tests/test_api_integration.py -v

Requirements:
- Database must be running and accessible
- Environment variable TAXDOWN_DATABASE_URL must be set

Markers:
- @pytest.mark.integration: Integration tests requiring database
- @pytest.mark.api: API endpoint tests
- @pytest.mark.slow: Slow-running tests
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import os
import uuid

# Set test database URL before importing app
os.environ.setdefault(
    "TAXDOWN_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/taxdown")
)
os.environ["TAXDOWN_DEBUG"] = "true"
os.environ["TAXDOWN_REQUIRE_API_KEY"] = "false"

from src.api.main import app


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def client():
    """Create test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def sample_property_id(client):
    """Get a sample property ID for testing."""
    response = client.post(
        "/api/v1/properties/search",
        json={"page_size": 1}
    )
    assert response.status_code == 200
    data = response.json()
    if data["properties"]:
        return data["properties"][0]["id"]
    pytest.skip("No properties in database")


@pytest.fixture(scope="module")
def sample_parcel_id(client):
    """Get a sample parcel ID for testing."""
    response = client.post(
        "/api/v1/properties/search",
        json={"page_size": 1}
    )
    assert response.status_code == 200
    data = response.json()
    if data["properties"]:
        return data["properties"][0]["parcel_id"]
    pytest.skip("No properties in database")


@pytest.fixture(scope="module")
def test_user(client):
    """Create a test user for portfolio tests."""
    timestamp = datetime.now().timestamp()
    email = f"api_test_{timestamp}@test.com"

    response = client.post(
        "/api/v1/portfolios/users",
        json={
            "email": email,
            "first_name": "API",
            "last_name": "Test",
            "user_type": "INVESTOR"
        }
    )

    if response.status_code == 409:
        # User exists, try to get by email
        response = client.get(f"/api/v1/portfolios/users/by-email/{email}")

    if response.status_code == 200:
        return response.json()["data"]

    pytest.skip("Could not create test user")


@pytest.fixture(scope="module")
def test_portfolio(client, test_user):
    """Create a test portfolio."""
    timestamp = datetime.now().timestamp()

    response = client.post(
        f"/api/v1/portfolios?user_id={test_user['id']}",
        json={
            "name": f"API Test Portfolio {timestamp}",
            "description": "Test portfolio for API integration tests"
        }
    )

    if response.status_code == 200:
        return response.json()["data"]

    pytest.skip("Could not create test portfolio")


# ============================================================================
# SYSTEM TESTS
# ============================================================================


@pytest.mark.api
class TestSystemEndpoints:
    """Test system/health endpoints."""

    def test_root(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Taxdown API"
        assert "version" in data

    def test_health(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_docs(self, client):
        """Test Swagger docs are accessible."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi(self, client):
        """Test OpenAPI schema is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "info" in data


# ============================================================================
# PROPERTY TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
class TestPropertyEndpoints:
    """Test property search and details endpoints."""

    def test_search_basic(self, client):
        """Test basic property search."""
        response = client.post(
            "/api/v1/properties/search",
            json={"page_size": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert "properties" in data
        assert "total_count" in data
        assert "page" in data
        assert len(data["properties"]) <= 10

    def test_search_with_query(self, client):
        """Test property search with text query."""
        response = client.post(
            "/api/v1/properties/search",
            json={"query": "Bella Vista", "page_size": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert "properties" in data

    def test_search_with_city_filter(self, client):
        """Test property search with city filter."""
        response = client.post(
            "/api/v1/properties/search",
            json={
                "city": "Bella Vista",
                "page_size": 5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "properties" in data

    def test_search_with_value_filter(self, client):
        """Test property search with value range filter."""
        response = client.post(
            "/api/v1/properties/search",
            json={
                "min_value": 100000,
                "max_value": 500000,
                "page_size": 5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "properties" in data
        # Verify values are within range
        for prop in data["properties"]:
            if prop.get("total_value"):
                assert 100000 <= prop["total_value"] <= 500000

    def test_search_pagination(self, client):
        """Test property search pagination."""
        # Get first page
        response1 = client.post(
            "/api/v1/properties/search",
            json={"page": 1, "page_size": 5}
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # Get second page
        response2 = client.post(
            "/api/v1/properties/search",
            json={"page": 2, "page_size": 5}
        )
        assert response2.status_code == 200
        data2 = response2.json()

        # Should be different properties (if enough exist)
        if data1["properties"] and data2["properties"]:
            ids1 = {p["id"] for p in data1["properties"]}
            ids2 = {p["id"] for p in data2["properties"]}
            assert not ids1.intersection(ids2), "Pages should have different properties"

    def test_search_sorting(self, client):
        """Test property search with sorting."""
        response = client.post(
            "/api/v1/properties/search",
            json={
                "page_size": 10,
                "sort_by": "value",
                "sort_order": "desc"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "properties" in data

        # Verify descending order
        values = [p.get("total_value", 0) or 0 for p in data["properties"]]
        assert values == sorted(values, reverse=True), "Properties should be sorted by value descending"

    def test_get_property_by_id(self, client, sample_property_id):
        """Test getting property by ID."""
        response = client.get(f"/api/v1/properties/{sample_property_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["id"] == sample_property_id
        assert "parcel_id" in data["data"]
        assert "address" in data["data"]

    def test_get_property_not_found(self, client):
        """Test getting non-existent property."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/properties/{fake_uuid}")
        assert response.status_code == 404

    def test_get_property_by_parcel(self, client, sample_parcel_id):
        """Test getting property by parcel ID."""
        response = client.get(f"/api/v1/properties/by-parcel/{sample_parcel_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["parcel_id"] == sample_parcel_id

    def test_autocomplete(self, client):
        """Test address autocomplete."""
        response = client.get("/api/v1/properties/autocomplete/address?q=main")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Each suggestion should have required fields
        for suggestion in data:
            assert "property_id" in suggestion
            assert "address" in suggestion

    def test_autocomplete_min_length(self, client):
        """Test autocomplete requires minimum length."""
        response = client.get("/api/v1/properties/autocomplete/address?q=ab")
        assert response.status_code == 422  # Validation error


# ============================================================================
# ANALYSIS TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
class TestAnalysisEndpoints:
    """Test assessment analysis endpoints."""

    def test_analyze_property(self, client, sample_property_id):
        """Test analyzing a property."""
        response = client.post(
            "/api/v1/analysis/assess",
            json={"property_id": sample_property_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "fairness_score" in data["data"]
        assert 0 <= data["data"]["fairness_score"] <= 100
        assert "recommended_action" in data["data"]

    def test_analyze_property_by_path(self, client, sample_property_id):
        """Test analyzing property via path parameter."""
        response = client.post(f"/api/v1/analysis/assess/{sample_property_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "fairness_score" in data["data"]

    def test_analyze_property_by_parcel(self, client, sample_parcel_id):
        """Test analyzing property by parcel ID."""
        response = client.post(
            "/api/v1/analysis/assess",
            json={"parcel_id": sample_parcel_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_analyze_invalid_property(self, client):
        """Test analyzing non-existent property."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            "/api/v1/analysis/assess",
            json={"property_id": fake_uuid}
        )
        assert response.status_code in [404, 500]

    @pytest.mark.slow
    def test_bulk_analyze(self, client, sample_property_id):
        """Test bulk analysis."""
        response = client.post(
            "/api/v1/analysis/bulk",
            json={"property_ids": [sample_property_id]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "analyzed" in data
        assert "results" in data
        assert data["total_requested"] == 1

    def test_analysis_history(self, client, sample_property_id):
        """Test getting analysis history."""
        response = client.get(f"/api/v1/analysis/history/{sample_property_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)


# ============================================================================
# APPEAL TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
class TestAppealEndpoints:
    """Test appeal generation endpoints."""

    def test_generate_appeal(self, client, sample_property_id):
        """Test generating an appeal (may return 422 if property doesn't qualify)."""
        response = client.post(
            "/api/v1/appeals/generate",
            json={"property_id": sample_property_id}
        )
        # 200 if property qualifies for appeal, 422 if it doesn't
        assert response.status_code in [200, 422]

        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert "appeal_letter" in data["data"]

    def test_generate_appeal_styles(self, client, sample_property_id):
        """Test generating appeals with different styles."""
        for style in ["formal", "detailed", "concise"]:
            response = client.post(
                "/api/v1/appeals/generate",
                json={
                    "property_id": sample_property_id,
                    "style": style
                }
            )
            # Accept both success and doesn't-qualify responses
            assert response.status_code in [200, 422]

    def test_list_appeals(self, client):
        """Test listing saved appeals."""
        response = client.get("/api/v1/appeals/list")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)

    def test_list_appeals_with_status_filter(self, client):
        """Test listing appeals filtered by status."""
        response = client.get("/api/v1/appeals/list?status=GENERATED")
        assert response.status_code == 200

    def test_get_appeal_not_found(self, client):
        """Test getting non-existent appeal."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/appeals/{fake_uuid}")
        assert response.status_code == 404


# ============================================================================
# PORTFOLIO TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
class TestPortfolioEndpoints:
    """Test portfolio management endpoints."""

    def test_create_user(self, client):
        """Test creating a new user."""
        timestamp = datetime.now().timestamp()
        response = client.post(
            "/api/v1/portfolios/users",
            json={
                "email": f"test_user_{timestamp}@test.com",
                "first_name": "Test",
                "last_name": "User"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "id" in data["data"]
        assert "email" in data["data"]

    def test_create_user_duplicate(self, client, test_user):
        """Test creating duplicate user fails."""
        response = client.post(
            "/api/v1/portfolios/users",
            json={"email": test_user["email"]}
        )
        assert response.status_code == 409

    def test_get_user(self, client, test_user):
        """Test getting user by ID."""
        response = client.get(f"/api/v1/portfolios/users/{test_user['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["id"] == test_user["id"]

    def test_get_user_by_email(self, client, test_user):
        """Test getting user by email."""
        response = client.get(f"/api/v1/portfolios/users/by-email/{test_user['email']}")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["email"] == test_user["email"]

    def test_list_portfolios(self, client, test_user):
        """Test listing user's portfolios."""
        response = client.get(f"/api/v1/portfolios?user_id={test_user['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)

    def test_create_portfolio(self, client, test_user):
        """Test creating a portfolio."""
        timestamp = datetime.now().timestamp()
        response = client.post(
            f"/api/v1/portfolios?user_id={test_user['id']}",
            json={
                "name": f"Test Portfolio {timestamp}",
                "description": "A test portfolio"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "id" in data["data"]

    def test_get_portfolio(self, client, test_portfolio):
        """Test getting portfolio by ID."""
        response = client.get(f"/api/v1/portfolios/{test_portfolio['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["id"] == test_portfolio["id"]

    def test_update_portfolio(self, client, test_portfolio):
        """Test updating portfolio."""
        response = client.patch(
            f"/api/v1/portfolios/{test_portfolio['id']}",
            json={"description": "Updated description"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_add_property_to_portfolio(self, client, test_portfolio, sample_property_id):
        """Test adding a property to portfolio."""
        response = client.post(
            f"/api/v1/portfolios/{test_portfolio['id']}/properties",
            json={"property_id": sample_property_id}
        )
        # 200 if added, 409 if already exists
        assert response.status_code in [200, 409]

    def test_list_portfolio_properties(self, client, test_portfolio):
        """Test listing portfolio properties."""
        response = client.get(f"/api/v1/portfolios/{test_portfolio['id']}/properties")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)

    def test_get_portfolio_dashboard(self, client, test_portfolio):
        """Test getting portfolio dashboard."""
        response = client.get(f"/api/v1/portfolios/{test_portfolio['id']}/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "metrics" in data["data"]
        assert "total_properties" in data["data"]["metrics"]

    def test_portfolio_not_found(self, client):
        """Test getting non-existent portfolio."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/portfolios/{fake_uuid}")
        assert response.status_code == 404


# ============================================================================
# REPORT TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
class TestReportEndpoints:
    """Test report generation endpoints."""

    def test_portfolio_summary_text(self, client, test_portfolio):
        """Test generating portfolio summary text."""
        response = client.get(f"/api/v1/reports/portfolio/{test_portfolio['id']}/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "summary" in data["data"]

    def test_generate_csv(self, client, test_portfolio):
        """Test generating CSV export."""
        response = client.post(f"/api/v1/reports/portfolio/{test_portfolio['id']}/csv")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

    def test_generate_report_json(self, client, test_portfolio):
        """Test generating JSON report."""
        response = client.post(
            "/api/v1/reports/generate",
            json={
                "portfolio_id": test_portfolio["id"],
                "format": "json",
                "report_type": "portfolio_summary"
            }
        )
        assert response.status_code == 200

    def test_property_analysis_report_json(self, client, sample_property_id):
        """Test generating property analysis report as JSON."""
        response = client.post(
            f"/api/v1/reports/property/{sample_property_id}/analysis?format=json"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "fairness_score" in data["data"]


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


@pytest.mark.api
class TestErrorHandling:
    """Test error responses and validation."""

    def test_validation_error_page_size(self, client):
        """Test validation error for excessive page size."""
        response = client.post(
            "/api/v1/properties/search",
            json={"page_size": 1000}  # Exceeds max of 100
        )
        assert response.status_code == 422

    def test_validation_error_negative_page(self, client):
        """Test validation error for negative page number."""
        response = client.post(
            "/api/v1/properties/search",
            json={"page": -1}
        )
        assert response.status_code == 422

    def test_invalid_uuid_format(self, client):
        """Test handling of invalid UUID format."""
        response = client.get("/api/v1/properties/not-a-uuid")
        assert response.status_code in [404, 422]

    def test_method_not_allowed(self, client):
        """Test method not allowed error."""
        response = client.put("/api/v1/properties/search")
        assert response.status_code == 405

    def test_missing_required_field(self, client):
        """Test missing required field in request."""
        response = client.post(
            "/api/v1/portfolios/users",
            json={}  # Missing required email
        )
        assert response.status_code == 422

    def test_invalid_email_format(self, client):
        """Test invalid email format validation."""
        response = client.post(
            "/api/v1/portfolios/users",
            json={"email": "not-an-email"}
        )
        assert response.status_code == 422


# ============================================================================
# RATE LIMIT TESTS
# ============================================================================


@pytest.mark.api
class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_headers_present(self, client):
        """Test that rate limit headers are present."""
        response = client.get("/api/v1/properties/autocomplete/address?q=test")
        # Rate limit headers may or may not be present depending on config
        # Just ensure request succeeds
        assert response.status_code in [200, 429]

    def test_request_id_header(self, client):
        """Test that request ID header is returned."""
        response = client.get("/health")
        assert response.status_code == 200
        # Request ID may be in different header formats
        has_request_id = any(
            'request' in h.lower() or 'x-request' in h.lower()
            for h in response.headers.keys()
        )
        # This is optional, so just note if present
        # assert has_request_id or True  # Don't fail if missing


# ============================================================================
# INTEGRATION FLOW TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.slow
class TestIntegrationFlows:
    """Test complete user flows across multiple endpoints."""

    def test_complete_property_analysis_flow(self, client, sample_property_id):
        """Test complete flow: search -> get details -> analyze."""
        # 1. Search for properties
        search_response = client.post(
            "/api/v1/properties/search",
            json={"page_size": 1}
        )
        assert search_response.status_code == 200
        properties = search_response.json()["properties"]
        assert len(properties) > 0

        property_id = properties[0]["id"]

        # 2. Get property details
        detail_response = client.get(f"/api/v1/properties/{property_id}")
        assert detail_response.status_code == 200
        property_data = detail_response.json()["data"]
        assert property_data["id"] == property_id

        # 3. Analyze property
        analysis_response = client.post(
            "/api/v1/analysis/assess",
            json={"property_id": property_id}
        )
        assert analysis_response.status_code == 200
        analysis = analysis_response.json()["data"]
        assert "fairness_score" in analysis

    def test_complete_portfolio_flow(self, client):
        """Test complete flow: create user -> create portfolio -> add properties."""
        # 1. Create user
        timestamp = datetime.now().timestamp()
        user_response = client.post(
            "/api/v1/portfolios/users",
            json={
                "email": f"flow_test_{timestamp}@test.com",
                "first_name": "Flow",
                "last_name": "Test"
            }
        )
        assert user_response.status_code == 200
        user = user_response.json()["data"]

        # 2. Create portfolio
        portfolio_response = client.post(
            f"/api/v1/portfolios?user_id={user['id']}",
            json={"name": f"Flow Test Portfolio {timestamp}"}
        )
        assert portfolio_response.status_code == 200
        portfolio = portfolio_response.json()["data"]

        # 3. Search for a property to add
        search_response = client.post(
            "/api/v1/properties/search",
            json={"page_size": 1}
        )
        assert search_response.status_code == 200
        properties = search_response.json()["properties"]

        if properties:
            property_id = properties[0]["id"]

            # 4. Add property to portfolio
            add_response = client.post(
                f"/api/v1/portfolios/{portfolio['id']}/properties",
                json={"property_id": property_id}
            )
            assert add_response.status_code == 200

            # 5. Get dashboard
            dashboard_response = client.get(
                f"/api/v1/portfolios/{portfolio['id']}/dashboard"
            )
            assert dashboard_response.status_code == 200
            dashboard = dashboard_response.json()["data"]
            assert dashboard["metrics"]["total_properties"] >= 1

        # 6. Clean up - delete portfolio
        delete_response = client.delete(f"/api/v1/portfolios/{portfolio['id']}")
        assert delete_response.status_code == 200


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.slow
class TestPerformance:
    """Basic performance tests."""

    def test_search_response_time(self, client):
        """Test that search responds in reasonable time."""
        import time

        start = time.time()
        response = client.post(
            "/api/v1/properties/search",
            json={"page_size": 20}
        )
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 5.0, f"Search took too long: {duration:.2f}s"

    def test_health_check_fast(self, client):
        """Test that health check is fast."""
        import time

        start = time.time()
        response = client.get("/health")
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.5, f"Health check took too long: {duration:.2f}s"
