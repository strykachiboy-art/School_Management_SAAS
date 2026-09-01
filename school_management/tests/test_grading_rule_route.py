def test_create_grading_rule_route_success(client, admin_headers, school):
    system_response = client.post(
        "/grading-systems/create",
        json={
            "name": "Rule System",
            "strategy": "LETTER_GRADE",
            "is_default": True,
            "school_id": school.id,
        },
        headers=admin_headers,
    )
    system_id = system_response.get_json()["id"]

    response = client.post(
        "/grading-rules/create",
        json={
            "grading_system_id": system_id,
            "grade_name": "A",
            "min_score": 70,
            "max_score": 100,
            "grade_point": 4.0,
            "remark": "Excellent",
            "display_order": 1,
        },
        headers=admin_headers,
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["grade_name"] == "A"
    assert payload["grading_system_id"] == system_id


def test_update_grading_rule_route_success(client, admin_headers, school):
    system_response = client.post(
        "/grading-systems/create",
        json={
            "name": "Rule Update System",
            "strategy": "LETTER_GRADE",
            "is_default": True,
            "school_id": school.id,
        },
        headers=admin_headers,
    )
    system_id = system_response.get_json()["id"]

    create_response = client.post(
        "/grading-rules/create",
        json={
            "grading_system_id": system_id,
            "grade_name": "B",
            "min_score": 60,
            "max_score": 69,
            "grade_point": 3.0,
            "remark": "Good",
            "display_order": 2,
        },
        headers=admin_headers,
    )
    rule_id = create_response.get_json()["id"]

    response = client.patch(
        f"/grading-rules/{rule_id}/edit",
        json={
            "grade_name": "B+",
            "min_score": 65,
            "remark": "Very Good",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["grade_name"] == "B+"
    assert payload["min_score"] == 65
    assert payload["remark"] == "Very Good"


def test_delete_grading_rule_route_success(client, admin_headers, school):
    system_response = client.post(
        "/grading-systems/create",
        json={
            "name": "Rule Delete System",
            "strategy": "LETTER_GRADE",
            "is_default": True,
            "school_id": school.id,
        },
        headers=admin_headers,
    )
    system_id = system_response.get_json()["id"]

    create_response = client.post(
        "/grading-rules/create",
        json={
            "grading_system_id": system_id,
            "grade_name": "C",
            "min_score": 50,
            "max_score": 59,
            "grade_point": 2.0,
            "remark": "Fair",
            "display_order": 3,
        },
        headers=admin_headers,
    )
    rule_id = create_response.get_json()["id"]

    response = client.delete(f"/grading-rules/{rule_id}", headers=admin_headers)

    assert response.status_code == 200
    assert response.get_json()["message"] == "Grading rule deleted successfully"
