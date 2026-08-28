from fastapi.testclient import TestClient


def test_finance_vertical_slice(client: TestClient) -> None:
    income_payloads = [
        {
            "received_date": "2026-06-25",
            "gross_amount": "3500000",
            "net_amount": "3000000",
            "income_type": "regular_salary",
            "source": "Employer",
            "classification": "guaranteed",
        },
        {
            "received_date": "2026-07-25",
            "gross_amount": "3500000",
            "net_amount": "3000000",
            "income_type": "regular_salary",
            "source": "Employer",
            "classification": "guaranteed",
        },
        {
            "received_date": "2026-07-25",
            "gross_amount": "11000000",
            "net_amount": "10000000",
            "income_type": "bonus",
            "source": "Employer",
            "classification": "exceptional",
        },
    ]
    for payload in income_payloads:
        assert client.post("/api/v1/incomes", json=payload).status_code == 201

    bill_response = client.post(
        "/api/v1/recurring-bills",
        json={
            "name": "Housing",
            "amount": "1000000",
            "category": "mortgage",
            "frequency": "monthly",
            "expected_payment_day": 10,
            "essential": True,
            "active": True,
            "effective_from": "2026-01-01",
        },
    )
    assert bill_response.status_code == 201

    goal_response = client.post(
        "/api/v1/goals",
        json={
            "name": "Emergency fund",
            "target_amount": "5000000",
            "current_amount": "2000000",
            "target_date": "2027-01-31",
            "priority": 1,
            "minimum_contribution": "300000",
            "preferred_contribution": "500000",
            "category": "emergency_fund",
            "status": "active",
            "progress_date": "2026-08-01",
        },
    )
    assert goal_response.status_code == 201
    goal_id = goal_response.json()["id"]

    progress_response = client.post(
        f"/api/v1/goals/{goal_id}/progress",
        json={"recorded_date": "2026-08-20", "current_amount": "2300000"},
    )
    assert progress_response.status_code == 201

    recommendation = client.get("/api/v1/budget/recommendation", params={"as_of": "2026-08-28"})
    assert recommendation.status_code == 200
    body = recommendation.json()
    assert body["budgetable_income"] == "3000000"
    assert body["recurring_bills_monthly"] == "1000000"
    assert body["required_goal_contributions"] == "450000"
    assert body["target_weekly"] == "268269"
    assert any("Exceptional income is excluded" in item for item in body["explanations"])


def test_rejects_fractional_krw(client: TestClient) -> None:
    response = client.post(
        "/api/v1/incomes",
        json={
            "received_date": "2026-07-25",
            "gross_amount": "1000.5",
            "net_amount": "900",
            "income_type": "other",
            "source": "Test",
            "classification": "variable",
        },
    )

    assert response.status_code == 422
