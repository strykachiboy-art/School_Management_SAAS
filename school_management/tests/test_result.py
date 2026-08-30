# test/test_result.py

JSON_HEADERS = {"Accept": "application/json"}


def test_create_result_success(client, admin_headers, student, exam):
    payload = {
        "student_id": student.id,
        "exam_id": exam.id,
        "marks_obtained": 92.5
    }
    
    headers = admin_headers.copy()
    headers["Accept"] = "application/json"
    
    # Use json=payload so Flask sends a proper JSON body for Pydantic validation
    response = client.post("/results/create", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.get_json()
    assert data["marks_obtained"] == 92.5
    assert data["student_id"] == student.id
    assert data["exam_id"] == exam.id

def test_create_result_validation_error(client, admin_headers):
    # Missing required fields like student_id or marks_obtained
    payload = {
        "exam_id": 1
    }
    headers = admin_headers.copy()
    headers["Accept"] = "application/json"
    
    # Use json=payload here as well
    response = client.post("/results/create", json=payload, headers=headers)
    assert response.status_code == 400

def test_get_all_results(client, admin_headers, result):
    headers = admin_headers.copy()
    headers["Accept"] = "application/json"
    
    response = client.get("/results/", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_get_result_by_id(client, admin_headers, result):
    headers = admin_headers.copy()
    headers["Accept"] = "application/json"
    
    response = client.get(f"/results/{result.id}", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == result.id
    assert data["marks_obtained"] == result.marks_obtained

def test_get_result_not_found(client, admin_headers):
    headers = admin_headers.copy()
    headers["Accept"] = "application/json"
    
    response = client.get("/results/9999", headers=headers)
    assert response.status_code == 404

def test_delete_result(client, admin_headers, result):
    headers = admin_headers.copy()
    headers["Accept"] = "application/json"
    
    response = client.delete(f"/results/{result.id}/delete", headers=headers)
    assert response.status_code == 200
    
    # Verify it is deleted
    check_response = client.get(f"/results/{result.id}", headers=headers)
    assert check_response.status_code == 404

def test_search_results_by_student(client, admin_headers, result, student):
    headers = admin_headers.copy()
    headers["Accept"] = "application/json"
    
    response = client.get(f"/results/search?student_id={student.id}", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["student_id"] == student.id

def test_search_results_pagination(client, admin_headers, result):
    headers = admin_headers.copy()
    headers["Accept"] = "application/json"
    
    response = client.get("/results/search?paginate=true", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "items" in data
    assert "page" in data
    assert "total" in data
    assert len(data["items"]) >= 1