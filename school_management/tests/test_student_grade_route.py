from school_app.models.result import Result


def test_get_my_grade_success(app, client, student, exam, make_result, student_headers):
    make_result(student_obj=student, exam_obj=exam, marks=80)

    response = client.get("/student/me/grade", headers=student_headers)

    assert response.status_code == 200
    data = response.get_json()
    assert "student_id" not in data
    assert data["average"] == 80
    assert data["grade"] == "A"
    assert data["remark"] == "Excelent"


def test_get_my_grade_no_results(client, student_headers):
    response = client.get("/student/me/grade", headers=student_headers)
    assert response.status_code == 404


def test_get_my_grade_no_profile(app, client):
    from flask_jwt_extended import create_access_token
    from school_app.models.user import User
    from school_app.extensions import db

    with app.app_context():
        user = User(username="notastudent", email="ns@example.com",
                    password="hashed-placeholder", role="teacher")
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)

        token = create_access_token(identity=str(user.id), additional_claims={"role": "teacher"})

    response = client.get("/student/me/grade",
                           headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    assert response.status_code == 403


def test_get_my_grade_requires_auth(client):
    response = client.get("/student/me/grade")
    assert response.status_code in (401, 422)