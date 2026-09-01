import pytest

from school_app.enums.reportcard import ReportCardStatus

# ======================================================================
# Calculate Report Card Tests
# ======================================================================


def test_calculate_report_card_as_teacher(
    client,
    teacher_headers,
    student,
    academic_session,
    term,
    make_exam,
    make_result,
):
  """A teacher can calculate a student's report card.

  This exercises the complete route -> service -> grade service flow.
  """
  exam = make_exam(
      suffix="report-card",
      term_obj=term,
      session_obj=academic_session,
  )

  make_result(
      student_obj=student,
      exam_obj=exam,
      marks=80,
  )

  response = client.post(
      "/report-cards/calculate",
      json={
          "student_id": student.id,
          "academic_session_id": academic_session.id,
          "term_id": term.id,
      },
      headers=teacher_headers,
  )

  assert response.status_code == 200

  data = response.get_json()

  assert data["student_id"] == student.id
  assert data["academic_session_id"] == academic_session.id
  assert data["term_id"] == term.id
  assert data["status"] == ReportCardStatus.CALCULATED.value
  assert data["public_reference"]

  assert data["summary_data"]["overall_average"] == pytest.approx(80.0)
  assert data["summary_data"]["grade"] == "A"
  assert data["summary_data"]["remark"] == "Excellent"


def test_calculate_report_card_as_admin(
    client,
    admin_headers,
    student,
    academic_session,
    term,
    make_exam,
    make_result,
):
  """An admin can calculate a student's report card."""
  exam = make_exam(
      suffix="admin-report-card",
      term_obj=term,
      session_obj=academic_session,
  )

  make_result(
      student_obj=student,
      exam_obj=exam,
      marks=65,
  )

  response = client.post(
      "/report-cards/calculate",
      json={
          "student_id": student.id,
          "academic_session_id": academic_session.id,
          "term_id": term.id,
      },
      headers=admin_headers,
  )

  assert response.status_code == 200

  data = response.get_json()

  assert data["status"] == ReportCardStatus.CALCULATED.value
  assert data["summary_data"]["overall_average"] == pytest.approx(65.0)
  assert data["summary_data"]["grade"] == "B"


def test_calculate_report_card_requires_authentication(
    client,
    student,
    academic_session,
    term,
):
  """Unauthenticated users cannot calculate report cards."""
  response = client.post(
      "/report-cards/calculate",
      json={
          "student_id": student.id,
          "academic_session_id": academic_session.id,
          "term_id": term.id,
      },
  )

  assert response.status_code in (401, 403)


def test_calculate_report_card_rejects_student_role(
    client,
    student_headers,
    student,
    academic_session,
    term,
):
  """Students are not allowed to calculate report cards."""
  response = client.post(
      "/report-cards/calculate",
      json={
          "student_id": student.id,
          "academic_session_id": academic_session.id,
          "term_id": term.id,
      },
      headers=student_headers,
  )

  assert response.status_code == 403


# ======================================================================
# Transition Status Tests
# ======================================================================


def test_transition_report_card_from_draft_to_calculated(
    client,
    teacher_headers,
    make_report_card,
):
  """A teacher can transition a report card from DRAFT to CALCULATED."""
  report = make_report_card(
      status=ReportCardStatus.DRAFT,
  )

  response = client.patch(
      f"/report-cards/{report.id}/status",
      json={
          "status": ReportCardStatus.CALCULATED.value,
      },
      headers=teacher_headers,
  )

  assert response.status_code == 200

  data = response.get_json()

  assert data["id"] == report.id
  assert data["status"] == ReportCardStatus.CALCULATED.value


def test_transition_report_card_rejects_invalid_transition(
    client,
    teacher_headers,
    make_report_card,
):
  """A report card cannot jump directly from DRAFT to PUBLISHED."""
  report = make_report_card(
      status=ReportCardStatus.DRAFT,
  )

  response = client.patch(
      f"/report-cards/{report.id}/status",
      json={
          "status": ReportCardStatus.PUBLISHED.value,
      },
      headers=teacher_headers,
  )

  assert response.status_code == 400


def test_transition_report_card_rejects_unauthorized_role(
    client,
    teacher_headers,
    make_report_card,
):
  """A teacher cannot move a CALCULATED report card to REVIEWED."""
  report = make_report_card(
      status=ReportCardStatus.CALCULATED,
  )

  response = client.patch(
      f"/report-cards/{report.id}/status",
      json={
          "status": ReportCardStatus.REVIEWED.value,
      },
      headers=teacher_headers,
  )

  assert response.status_code == 403


def test_transition_report_card_not_found(
    client,
    teacher_headers,
):
  """Transitioning a nonexistent report card returns 404."""
  response = client.patch(
      "/report-cards/999999/status",
      json={
          "status": ReportCardStatus.CALCULATED.value,
      },
      headers=teacher_headers,
  )

  assert response.status_code == 404


# ======================================================================
# Set Access PIN Tests
# ======================================================================


def test_set_report_card_access_pin(
    client,
    admin_headers,
    make_report_card,
):
  """An admin can set an access PIN on a report card."""
  report = make_report_card()

  response = client.post(
      f"/report-cards/{report.id}/pin",
      json={
          "pin": "1234",
      },
      headers=admin_headers,
  )

  assert response.status_code == 200

  data = response.get_json()

  assert data == {
      "message": "Access PIN updated successfully",
  }


def test_set_report_card_access_pin_requires_admin(
    client,
    teacher_headers,
    make_report_card,
):
  """Teachers cannot set report-card access PINs."""
  report = make_report_card()

  response = client.post(
      f"/report-cards/{report.id}/pin",
      json={
          "pin": "1234",
      },
      headers=teacher_headers,
  )

  assert response.status_code == 403


def test_set_report_card_access_pin_rejects_short_pin(
    client,
    admin_headers,
    make_report_card,
):
  """PIN validation requires at least four characters."""
  report = make_report_card()

  response = client.post(
      f"/report-cards/{report.id}/pin",
      json={
          "pin": "123",
      },
      headers=admin_headers,
  )

  assert response.status_code == 400


def test_set_report_card_access_pin_not_found(
    client,
    admin_headers,
):
  """Setting a PIN on a nonexistent report card returns 404."""
  response = client.post(
      "/report-cards/999999/pin",
      json={
          "pin": "1234",
      },
      headers=admin_headers,
  )

  assert response.status_code == 404


# ======================================================================
# Public Verification Tests
# ======================================================================


def test_public_verify_published_report_without_pin(
    client,
    make_report_card,
):
  """A published report card without a PIN can be publicly verified."""
  report = make_report_card(
      status=ReportCardStatus.PUBLISHED,
      summary_data={
          "subject_scores": {},
          "overall_average": 75.0,
          "grade": "A",
          "remark": "Excellent",
      },
  )

  response = client.post(
      "/report-cards/public/verify",
      json={
          "reference": report.public_reference,
      },
  )

  assert response.status_code == 200

  data = response.get_json()

  assert data["id"] == report.id
  assert data["student_id"] == report.student_id
  assert data["status"] == ReportCardStatus.PUBLISHED.value
  assert data["public_reference"] == report.public_reference
  assert data["summary_data"]["overall_average"] == 75.0


def test_public_verify_published_report_with_correct_pin(
    client,
    make_report_card,
):
  """A published report card with a PIN accepts the correct PIN."""
  report = make_report_card(
      status=ReportCardStatus.PUBLISHED,
      access_pin="1234",
  )

  response = client.post(
      "/report-cards/public/verify",
      json={
          "reference": report.public_reference,
          "pin": "1234",
      },
  )

  assert response.status_code == 200

  data = response.get_json()

  assert data["id"] == report.id
  assert data["public_reference"] == report.public_reference
  assert data["status"] == ReportCardStatus.PUBLISHED.value


def test_public_verify_rejects_wrong_pin(
    client,
    make_report_card,
):
  """A published report card rejects an incorrect PIN."""
  report = make_report_card(
      status=ReportCardStatus.PUBLISHED,
      access_pin="1234",
  )

  response = client.post(
      "/report-cards/public/verify",
      json={
          "reference": report.public_reference,
          "pin": "9999",
      },
  )

  assert response.status_code == 403


def test_public_verify_rejects_missing_pin_when_required(
    client,
    make_report_card,
):
  """A PIN-protected report card requires the correct PIN."""
  report = make_report_card(
      status=ReportCardStatus.PUBLISHED,
      access_pin="1234",
  )

  response = client.post(
      "/report-cards/public/verify",
      json={
          "reference": report.public_reference,
      },
  )

  assert response.status_code == 403


def test_public_verify_rejects_unpublished_report(
    client,
    make_report_card,
):
  """Only PUBLISHED report cards are publicly accessible."""
  report = make_report_card(
      status=ReportCardStatus.DRAFT,
  )

  response = client.post(
      "/report-cards/public/verify",
      json={
          "reference": report.public_reference,
      },
  )

  assert response.status_code == 404


def test_public_verify_rejects_invalid_reference(
    client,
):
  """An unknown public reference returns 404."""
  response = client.post(
      "/report-cards/public/verify",
      json={
          "reference": "does-not-exist",
      },
  )

  assert response.status_code == 404