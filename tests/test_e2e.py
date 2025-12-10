"""
End-to-End Tests for Taxdown

Tests the complete workflow from property search to appeal generation.
"""

import pytest
from fastapi.testclient import TestClient
import os

os.environ["TAXDOWN_DATABASE_URL"] = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/taxdown"
)

from src.api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestCompleteWorkflow:
    """Test the complete user workflow."""

    def test_01_health_check(self, client):
        """Verify API is running."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_02_search_properties(self, client):
        """Search for properties in Bella Vista."""
        response = client.post(
            "/api/v1/properties/search",
            json={"query": "Bella Vista", "page_size": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] > 0

        # Store first property for later tests
        self.__class__.test_property = data["properties"][0]

    def test_03_get_property_details(self, client):
        """Get details for a specific property."""
        property_id = self.test_property["id"]
        response = client.get(f"/api/v1/properties/{property_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["parcel_id"] == self.test_property["parcel_id"]

    def test_04_analyze_property(self, client):
        """Run assessment analysis."""
        property_id = self.test_property["id"]
        response = client.post(
            "/api/v1/analysis/assess",
            json={"property_id": property_id, "include_comparables": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert "fairness_score" in data["data"]
        assert 0 <= data["data"]["fairness_score"] <= 100

        self.__class__.analysis_result = data["data"]

    def test_05_check_analysis_history(self, client):
        """Verify analysis was saved."""
        property_id = self.test_property["id"]
        response = client.get(f"/api/v1/analysis/history/{property_id}")
        assert response.status_code == 200

    def test_06_generate_appeal_if_qualified(self, client):
        """Generate appeal if property qualifies."""
        # NEW SCORING: lower score = more over-assessed, qualifies for appeal
        # Score > 60 means fairly assessed, doesn't qualify
        if self.analysis_result["fairness_score"] > 60:
            pytest.skip("Property doesn't qualify for appeal (score > 60 means fairly assessed)")

        property_id = self.test_property["id"]
        response = client.post(
            "/api/v1/appeals/generate",
            json={"property_id": property_id, "style": "formal"}
        )

        # May be 200 (success) or 422 (doesn't qualify)
        assert response.status_code in [200, 422]

        if response.status_code == 200:
            data = response.json()
            assert "letter_content" in data["data"]
            self.__class__.appeal = data["data"]

    def test_07_list_appeals(self, client):
        """List all appeals."""
        response = client.get("/api/v1/appeals/list")
        assert response.status_code == 200


class TestUserWorkflow:
    """Test user and portfolio workflow."""

    @pytest.fixture(autouse=True)
    def setup(self, client):
        self.client = client
        self.test_email = f"e2e_test_{os.urandom(4).hex()}@test.com"

    def test_create_user(self):
        response = self.client.post(
            "/api/v1/portfolios/users",
            json={"email": self.test_email, "first_name": "E2E", "last_name": "Test"}
        )
        assert response.status_code == 200
        self.user_id = response.json()["data"]["id"]

    def test_create_portfolio(self):
        # First create user
        response = self.client.post(
            "/api/v1/portfolios/users",
            json={"email": self.test_email}
        )
        user_id = response.json()["data"]["id"]

        # Create portfolio
        response = self.client.post(
            f"/api/v1/portfolios?user_id={user_id}",
            json={"name": "E2E Test Portfolio"}
        )
        assert response.status_code == 200
        portfolio_id = response.json()["data"]["id"]

        # Get a property to add
        props = self.client.post(
            "/api/v1/properties/search",
            json={"page_size": 1}
        ).json()

        if props["properties"]:
            # Add property to portfolio
            response = self.client.post(
                f"/api/v1/portfolios/{portfolio_id}/properties",
                json={"property_id": props["properties"][0]["id"]}
            )
            assert response.status_code in [200, 409]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_property_id(self, client):
        response = client.get("/api/v1/properties/invalid-uuid")
        assert response.status_code == 404

    def test_invalid_search_params(self, client):
        response = client.post(
            "/api/v1/properties/search",
            json={"page_size": 10000}  # Exceeds max
        )
        assert response.status_code == 422

    def test_analyze_nonexistent_property(self, client):
        response = client.post(
            "/api/v1/analysis/assess",
            json={"property_id": "00000000-0000-0000-0000-000000000000"}
        )
        assert response.status_code in [404, 500]

    def test_empty_search(self, client):
        response = client.post(
            "/api/v1/properties/search",
            json={"query": "xyznonexistent12345"}
        )
        assert response.status_code == 200
        assert response.json()["total_count"] == 0


class TestPerformance:
    """Basic performance tests."""

    def test_search_response_time(self, client):
        import time
        start = time.time()
        response = client.post(
            "/api/v1/properties/search",
            json={"page_size": 20}
        )
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 2.0, f"Search took {elapsed:.2f}s, expected < 2s"

    def test_analysis_response_time(self, client):
        import time

        # Get a property
        props = client.post(
            "/api/v1/properties/search",
            json={"page_size": 1}
        ).json()

        if not props["properties"]:
            pytest.skip("No properties available")

        property_id = props["properties"][0]["id"]

        start = time.time()
        response = client.post(
            "/api/v1/analysis/assess",
            json={"property_id": property_id}
        )
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 5.0, f"Analysis took {elapsed:.2f}s, expected < 5s"
