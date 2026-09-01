import uuid
from datetime import date, timedelta

import pytest


# ======================================================================
# Create Teacher
# ======================================================================

def test_create_teacher_success(client, admin_headers):
    unique_suffix = uuid.uuid4().hex[:6]

    payload = {
        "username": f"new_teacher_{unique_suffix}",
        "full_name": "Jane Doe",
        "email": f"jane.doe_{unique_suffix}@example.com",
        "phone": "1234567890",
        "gender": "female",
        "date_of_birth": "1995-05-15",
        "password": "securepass123",
    }

    response = client.post(
        "/teachers/create",
        json=payload,
        headers=admin_headers,
    )

    if response.status_code != 201:
        print("RESPONSE ERROR:", response.get_json())

    assert response.status_code == 201

    data = response.get_json()

    assert data["full_name"] == "Jane Doe"
    assert data["email"] == f"jane.doe_{unique_suffix}@example.com"
    assert data["phone"] == "1234567890"
    assert data["gender"] == "female"
    assert data["date_of_birth"] == "1995-05-15"
    assert "id" in data
    assert "user_id" in data


def test_create_teacher_duplicate_username(
    client,
    admin_headers,
    teacher,
):
    """A duplicate username should return 400."""

    payload = {
        "username": "teacher_1",
        "full_name": "Duplicate Teacher",
        "email": f"unique_{uuid.uuid4().hex[:6]}@example.com",
        "phone": "1234567890",
        "gender": "male",
        "password": "securepass123",
    }

    response = client.post(
        "/teachers/create",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_create_teacher_duplicate_email(
    client,
    admin_headers,
    teacher,
):
    """A duplicate email should return 400."""

    payload = {
        "username": f"duplicate_email_{uuid.uuid4().hex[:6]}",
        "full_name": "Duplicate Email",
        "email": teacher.email,
        "phone": "1234567890",
        "gender": "male",
        "password": "securepass123",
    }

    response = client.post(
        "/teachers/create",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 400


# ======================================================================
# Create Teacher Validation
# ======================================================================

def test_create_teacher_blank_full_name(
    client,
    admin_headers,
):
    payload = {
        "username": f"blank_name_{uuid.uuid4().hex[:6]}",
        "full_name": "   ",
        "email": f"blank_{uuid.uuid4().hex[:6]}@example.com",
        "password": "securepass123",
    }

    response = client.post(
        "/teachers/create",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_create_teacher_invalid_phone(
    client,
    admin_headers,
):
    payload = {
        "username": f"bad_phone_{uuid.uuid4().hex[:6]}",
        "full_name": "Bad Phone",
        "email": f"phone_{uuid.uuid4().hex[:6]}@example.com",
        "phone": "123-456-7890",
        "password": "securepass123",
    }

    response = client.post(
        "/teachers/create",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_create_teacher_invalid_gender(
    client,
    admin_headers,
):
    payload = {
        "username": f"bad_gender_{uuid.uuid4().hex[:6]}",
        "full_name": "Bad Gender",
        "email": f"gender_{uuid.uuid4().hex[:6]}@example.com",
        "gender": "invalid",
        "password": "securepass123",
    }

    response = client.post(
        "/teachers/create",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_create_teacher_future_date_of_birth(
    client,
    admin_headers,
):
    future_date = date.today() + timedelta(days=1)

    payload = {
        "username": f"future_dob_{uuid.uuid4().hex[:6]}",
        "full_name": "Future DOB",
        "email": f"future_{uuid.uuid4().hex[:6]}@example.com",
        "date_of_birth": future_date.isoformat(),
        "password": "securepass123",
    }

    response = client.post(
        "/teachers/create",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_create_teacher_short_password(
    client,
    admin_headers,
):
    payload = {
        "username": f"short_pass_{uuid.uuid4().hex[:6]}",
        "full_name": "Short Password",
        "email": f"password_{uuid.uuid4().hex[:6]}@example.com",
        "password": "123",
    }

    response = client.post(
        "/teachers/create",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_create_teacher_invalid_username(
    client,
    admin_headers,
):
    payload = {
        "username": "bad-user!",
        "full_name": "Bad Username",
        "email": f"username_{uuid.uuid4().hex[:6]}@example.com",
        "password": "securepass123",
    }

    response = client.post(
        "/teachers/create",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 400


# ======================================================================
# Get Teacher
# ======================================================================

def test_get_teacher_success(
    client,
    admin_headers,
    teacher,
):
    response = client.get(
        f"/teachers/{teacher.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["id"] == teacher.id
    assert data["user_id"] == teacher.user_id
    assert data["full_name"] == teacher.full_name


def test_get_teacher_not_found(
    client,
    admin_headers,
):
    response = client.get(
        "/teachers/99999",
        headers=admin_headers,
    )

    assert response.status_code == 404


# ======================================================================
# Get All Teachers
# ======================================================================

def test_get_all_teachers(
    client,
    admin_headers,
    teacher,
):
    response = client.get(
        "/teachers",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert isinstance(data, list)
    assert any(item["id"] == teacher.id for item in data)


# ======================================================================
# Search Teachers
# ======================================================================

def test_search_teachers_by_name(
    client,
    admin_headers,
    teacher,
):
    response = client.get(
        f"/teachers?search={teacher.full_name}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert isinstance(data, list)
    assert any(item["id"] == teacher.id for item in data)


def test_search_teachers_no_match(
    client,
    admin_headers,
):
    response = client.get(
        "/teachers?search=this_teacher_should_not_exist",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert isinstance(data, list)
    assert data == []


# ======================================================================
# Filter Teachers
# ======================================================================

def test_filter_teacher_by_id(
    client,
    admin_headers,
    teacher,
):
    response = client.get(
        f"/teachers?id={teacher.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1
    assert data[0]["id"] == teacher.id


def test_filter_teacher_by_user_id(
    client,
    admin_headers,
    teacher,
):
    response = client.get(
        f"/teachers?user_id={teacher.user_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1
    assert data[0]["user_id"] == teacher.user_id


# ======================================================================
# Pagination
# ======================================================================

def test_get_teachers_paginated(
    client,
    admin_headers,
    teacher,
):
    response = client.get(
        "/teachers?paginate=true",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert "items" in data
    assert "page" in data
    assert "pages" in data
    assert "total" in data

    assert isinstance(data["items"], list)
    assert data["page"] == 1
    assert data["total"] >= 1


# ======================================================================
# Update Teacher
# ======================================================================

def test_update_teacher_success(
    client,
    admin_headers,
    teacher,
):
    payload = {
        "full_name": "Updated Teacher Name",
        "email": f"updated_{uuid.uuid4().hex[:6]}@example.com",
        "phone": "08012345678",
        "gender": "female",
        "date_of_birth": "1990-01-01",
    }

    response = client.put(
        f"/teachers/{teacher.id}/edit",
        json=payload,
        headers=admin_headers,
    )

    if response.status_code != 200:
        print("RESPONSE ERROR:", response.get_json())

    assert response.status_code == 200

    data = response.get_json()

    assert data["id"] == teacher.id
    assert data["full_name"] == "Updated Teacher Name"
    assert data["email"] == payload["email"]
    assert data["phone"] == "08012345678"
    assert data["gender"] == "female"
    assert data["date_of_birth"] == "1990-01-01"


def test_patch_teacher_success(
    client,
    admin_headers,
    teacher,
):
    payload = {
        "full_name": "Patched Teacher",
    }

    response = client.patch(
        f"/teachers/{teacher.id}/edit",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["id"] == teacher.id
    assert data["full_name"] == "Patched Teacher"


def test_update_teacher_not_found(
    client,
    admin_headers,
):
    payload = {
        "full_name": "Does Not Exist",
    }

    response = client.put(
        "/teachers/99999/edit",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_update_teacher_invalid_phone(
    client,
    admin_headers,
    teacher,
):
    payload = {
        "full_name": "Updated Teacher",
        "phone": "123-456",
    }

    response = client.put(
        f"/teachers/{teacher.id}/edit",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 400


# ======================================================================
# Delete Teacher
# ======================================================================

def test_delete_teacher_success(
    client,
    admin_headers,
    teacher,
):
    response = client.delete(
        f"/teachers/{teacher.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["message"] == "Teacher deleted successfully"


def test_delete_teacher_not_found(
    client,
    admin_headers,
):
    response = client.delete(
        "/teachers/99999",
        headers=admin_headers,
    )

    assert response.status_code == 404