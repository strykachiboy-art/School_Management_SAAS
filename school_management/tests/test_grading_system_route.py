def test_create_grading_system_route_success(client, admin_headers, school):
    response = client.post(
        "/grading-systems/create",
        json={
            "name": "School Grading System",
            "strategy": "letter_grade",
            "is_default": True,
            "school_id": school.id,
        },
        headers=admin_headers,
    )

    assert response.status_code == 201

    payload = response.get_json()

    assert payload["name"] == "School Grading System"
    assert payload["strategy"] == "letter_grade"
    assert payload["is_default"] is True
    assert payload["school_id"] == school.id


def test_get_all_grading_systems_route_returns_list(client, admin_headers, school):
    response = client.post(
        "/grading-systems/create",
        json={
            "name": "System A",
            "strategy": "letter_grade",
            "is_default": True,
            "school_id": school.id,
        },
        headers=admin_headers,
    )

    assert response.status_code == 201

    response = client.get("/grading-systems", headers=admin_headers)

    assert response.status_code == 200

    payload = response.get_json()

    assert isinstance(payload, list)
    assert any(item["name"] == "System A" for item in payload)


def test_get_single_grading_system_route_returns_404_for_missing_id(
    client,
    admin_headers,
):
    response = client.get(
        "/grading-systems/999999",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_update_grading_system_route_success(client, admin_headers, school):
    create_response = client.post(
        "/grading-systems/create",
        json={
            "name": "Old System",
            "strategy": "letter_grade",
            "is_default": False,
            "school_id": school.id,
        },
        headers=admin_headers,
    )

    assert create_response.status_code == 201

    system_id = create_response.get_json()["id"]

    response = client.patch(
        f"/grading-systems/{system_id}/edit",
        json={
            "name": "Updated System",
            "is_default": True,
            "is_active": True,
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert payload["name"] == "Updated System"
    assert payload["is_default"] is True


def test_delete_grading_system_route_success(client, admin_headers, school):
    create_response = client.post(
        "/grading-systems/create",
        json={
            "name": "Delete Me",
            "strategy": "letter_grade",
            "is_default": False,
            "school_id": school.id,
        },
        headers=admin_headers,
    )

    assert create_response.status_code == 201

    system_id = create_response.get_json()["id"]

    response = client.delete(
        f"/grading-systems/{system_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == (
        "Grading system deleted successfully"
    )