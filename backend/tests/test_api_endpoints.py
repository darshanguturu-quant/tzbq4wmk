"""
Integration and API endpoint tests using FastAPI TestClient.
Verifies all routes in PRD Section 11 and Section 15.2.
"""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp_utc" in data
    assert data["snapshot_loaded"] is True


def test_metadata_endpoint():
    response = client.get("/api/metadata")
    assert response.status_code == 200
    data = response.json()
    assert "scope" in data
    assert len(data["cutoff_presets"]) == 3
    assert data["default_cutoff"] == "09:20"
    assert "disclaimers" in data
    assert "cutoff" in data["disclaimers"]


def test_decision_profile_replay_mode_hides_actuals():
    """In replay mode (include_actuals=false), actuals must never appear."""
    response = client.get(
        "/api/decision-profile?decision_date=2026-01-15&cutoff=09:20&include_actuals=false"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision_date"] == "2026-01-15"
    assert data["delivery_date"] == "2026-01-16"
    assert data["expected_intervals"] == 24
    assert len(data["intervals"]) == 24

    for interval in data["intervals"]:
        assert interval["actual_mw"] is None
        assert interval["error_mw"] is None
        assert interval["forecast_mw"] is not None


def test_decision_profile_outcome_mode_shows_actuals():
    """In outcome review mode (include_actuals=true), actuals and errors are present."""
    response = client.get(
        "/api/decision-profile?decision_date=2026-01-15&cutoff=09:20&include_actuals=true"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["matched_intervals"] == 24

    first = data["intervals"][0]
    assert first["forecast_mw"] is not None
    assert first["actual_mw"] is not None
    assert first["error_mw"] is not None


def test_decision_profile_validation_dates_outside_january():
    """Decision date outside January 2026 must return 400."""
    response = client.get("/api/decision-profile?decision_date=2025-12-31&cutoff=09:20")
    assert response.status_code == 400
    assert "outside January 2026" in response.json()["detail"]

    response2 = client.get(
        "/api/decision-profile?decision_date=2026-02-01&cutoff=09:20"
    )
    assert response2.status_code == 400


def test_decision_profile_validation_malformed_cutoff():
    """Malformed cutoff time must return 400."""
    response = client.get("/api/decision-profile?decision_date=2026-01-15&cutoff=25:00")
    assert response.status_code == 400

    response2 = client.get(
        "/api/decision-profile?decision_date=2026-01-15&cutoff=bad_time"
    )
    assert response2.status_code == 400


def test_performance_endpoint():
    response = client.get(
        "/api/performance?cutoff=09:20&start_date=2026-01-01&end_date=2026-01-31"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["headline"]["n_matched"] > 0
    assert data["headline"]["mae_mw"] > 0
    assert len(data["hourly_breakdown"]) == 24
    assert len(data["daily_breakdown"]) == 31
    assert "so_what" in data


def test_performance_date_range_validation():
    """start_date > end_date must return 400."""
    response = client.get(
        "/api/performance?cutoff=09:20&start_date=2026-01-20&end_date=2026-01-10"
    )
    assert response.status_code == 400
    assert "cannot be after" in response.json()["detail"]


def test_performance_compare_endpoint():
    response = client.get(
        "/api/performance/compare?cutoffs=09:20,09:50,15:30&start_date=2026-01-01&end_date=2026-01-15"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # All must have the same number of common matched intervals
    assert (
        data[0]["n_common_intervals"]
        == data[1]["n_common_intervals"]
        == data[2]["n_common_intervals"]
    )


def test_data_quality_endpoint():
    response = client.get(
        "/api/data-quality?cutoff=09:20&start_date=2026-01-01&end_date=2026-01-31"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["expected_intervals"] == 31 * 24
    assert data["matched_pairs"] > 0
    assert "snapshot_sha256" in data
    assert "negative_lead_rows_excluded" in data


def test_export_csv_endpoint():
    response = client.get(
        "/api/export?cutoff=09:20&start_date=2026-01-01&end_date=2026-01-05"
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    lines = [
        line.strip() for line in response.text.strip().splitlines() if line.strip()
    ]
    assert len(lines) > 1  # Header + rows
    header = lines[0].split(",")
    assert "forecast_mw" in header
    assert "actual_mw" in header
    assert "error_mw" in header
