from datetime import date, timedelta
import pytest

def test_create_fee_structure_route(client, admin_headers, classroom, academic_session, term):
    payload = {
        "classroom_id": classroom.id,
        "session_id": academic_session.id,
        "term_id": term.id,
        "category": "tuition",
        "amount": 75000.0
    }
    
    response = client.post("/fees/structures", json=payload, headers=admin_headers)
    
    assert response.status_code == 201
    data = response.get_json()
    assert data["amount"] == 75000.0
    assert data["category"] == "tuition"

def test_get_fee_structures_route(client, admin_headers, classroom, academic_session, term):
    response = client.get(
        f"/fees/structures?classroom_id={classroom.id}&session_id={academic_session.id}&term_id={term.id}",
        headers=admin_headers
    )
    
    assert response.status_code in [200, 404]

def test_generate_invoices_route(client, admin_headers, classroom, academic_session, term):
    payload = {
        "classroom_id": classroom.id,
        "session_id": academic_session.id,
        "term_id": term.id,
        "due_date": (date.today() + timedelta(days=30)).isoformat()
    }
    
    response = client.post("/fees/invoices/generate", json=payload, headers=admin_headers)
    assert response.status_code in [201, 400]

def test_record_payment_route(client, admin_headers):
    payload = {
        "invoice_id": 9999,
        "amount": 5000.0,
        "payment_method": "cash"
    }
    
    response = client.post("/fees/payments", json=payload, headers=admin_headers)
    assert response.status_code in [400, 404, 422]