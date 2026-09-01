# tests/test_admin_report_students.py

from datetime import date
from decimal import Decimal

from school_app.models.academic_session import AcademicSession
from school_app.models.term import Term
from school_app.models.classroom import Classroom
from school_app.models.subject import Subject
from school_app.models.school_fees import Invoice, Payment
from school_app.enums.school_fees import PaymentStatus, PaymentMethod

from school_app.modules.admin_reports.services.admin_report_students_service import (
    get_admin_report_students,
)


def test_get_admin_report_students_comprehensive(app, db_session, school, make_student):
    """
    Test student report generation, including filters, aggregations,
    and individual student metrics.
    """
    with app.app_context():
        # ------------------------------------------------------------
        # 1. Use the existing school fixture (do not create another School)
        # ------------------------------------------------------------

        # ------------------------------------------------------------
        # 2. Academic session
        # ------------------------------------------------------------
        session = AcademicSession(
            school_id=school.id,
            name="2025/2026",
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
        )
        db_session.add(session)
        db_session.flush()

        # ------------------------------------------------------------
        # 3. Term
        # ------------------------------------------------------------
        term = Term(
            school_id=school.id,
            name="First Term",
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 1),
            academic_session_id=session.id,
        )
        db_session.add(term)
        db_session.flush()

        # ------------------------------------------------------------
        # 4. Classroom
        # ------------------------------------------------------------
        classroom = Classroom(
            school_id=school.id,
            name="Grade 10A",
            capacity=30,
        )
        db_session.add(classroom)
        db_session.flush()

        # ------------------------------------------------------------
        # 5. Subject
        # ------------------------------------------------------------
        subject = Subject(
            school_id=school.id,
            name="Mathematics",
            code="MATH101",
        )
        db_session.add(subject)
        db_session.flush()

        # ------------------------------------------------------------
        # 6. Students
        # ------------------------------------------------------------
        # Use the existing fixture because Student.user_id is NOT NULL.
        student1 = make_student("students_alice")
        student2 = make_student("students_bob")
        student3 = make_student("students_charlie")

        # Merge into session and attach to classroom
        student1 = db_session.merge(student1)
        student2 = db_session.merge(student2)
        student3 = db_session.merge(student3)

        student1.classroom_id = classroom.id
        student2.classroom_id = classroom.id
        student3.classroom_id = classroom.id

        db_session.flush()

        # ------------------------------------------------------------
        # 7. Create invoices for each student (used by student report metrics)
        # ------------------------------------------------------------
        inv1 = Invoice(
            school_id=school.id,
            student_id=student1.id,
            session_id=session.id,
            term_id=term.id,
            total_amount=Decimal("120.00"),
        )

        inv2 = Invoice(
            school_id=school.id,
            student_id=student2.id,
            session_id=session.id,
            term_id=term.id,
            total_amount=Decimal("80.00"),
        )

        inv3 = Invoice(
            school_id=school.id,
            student_id=student3.id,
            session_id=session.id,
            term_id=term.id,
            total_amount=Decimal("100.00"),
        )

        db_session.add_all([inv1, inv2, inv3])
        db_session.flush()

        # ------------------------------------------------------------
        # 8. Create payments to produce different student statuses
        # ------------------------------------------------------------
        # Alice: fully paid
        payment_alice = Payment(
            school_id=school.id,
            invoice_id=inv1.id,
            student_id=student1.id,
            amount=Decimal("120.00"),
            status=PaymentStatus.CONFIRMED,
            payment_method=PaymentMethod.CASH,
            reference="STU-PAY-001",
        )

        # Bob: partially paid
        payment_bob = Payment(
            school_id=school.id,
            invoice_id=inv2.id,
            student_id=student2.id,
            amount=Decimal("30.00"),
            status=PaymentStatus.CONFIRMED,
            payment_method=PaymentMethod.BANK_TRANSFER,
            reference="STU-PAY-002",
        )

        # Charlie: no confirmed payments (unpaid) — add a failed payment to ensure it doesn't count
        payment_charlie_failed = Payment(
            school_id=school.id,
            invoice_id=inv3.id,
            student_id=student3.id,
            amount=Decimal("100.00"),
            status=PaymentStatus.FAILED,
            payment_method=PaymentMethod.BANK_TRANSFER,
            reference="STU-PAY-003",
        )

        db_session.add_all([payment_alice, payment_bob, payment_charlie_failed])
        db_session.commit()

        # ------------------------------------------------------------
        # 9. Generate student report
        # ------------------------------------------------------------
        report = get_admin_report_students(session_id=session.id, term_id=term.id)

        # ------------------------------------------------------------
        # 10. Basic assertions about returned structure
        # ------------------------------------------------------------
        assert isinstance(report, dict)
        assert "students" in report
        assert isinstance(report["students"], list)

        # ------------------------------------------------------------
        # 11. Find individual student entries and assert metrics
        # ------------------------------------------------------------
        students_by_id = {s["student_id"]: s for s in report["students"]}

        # Alice should be fully paid
        alice_entry = students_by_id.get(student1.id)
        assert alice_entry is not None
        assert alice_entry.get("total_expected") == float(inv1.total_amount)
        assert alice_entry.get("total_paid") == 120.0
        assert alice_entry.get("status") in ("fully_paid", "FULLY_PAID", "Fully Paid", "paid")

        # Bob should be partially paid
        bob_entry = students_by_id.get(student2.id)
        assert bob_entry is not None
        assert bob_entry.get("total_expected") == float(inv2.total_amount)
        assert bob_entry.get("total_paid") == 30.0
        assert bob_entry.get("status") in ("partially_paid", "PARTIALLY_PAID", "Partially Paid", "partial")

        # Charlie should be unpaid
        charlie_entry = students_by_id.get(student3.id)
        assert charlie_entry is not None
        assert charlie_entry.get("total_expected") == float(inv3.total_amount)
        assert charlie_entry.get("total_paid") == 0.0
        assert charlie_entry.get("status") in ("unpaid", "UNPAID", "Unpaid", "none")

        # ------------------------------------------------------------
        # 12. Aggregations sanity checks
        # ------------------------------------------------------------
        total_expected = sum(s["total_expected"] for s in report["students"])
        total_paid = sum(s["total_paid"] for s in report["students"])

        assert total_expected == float(inv1.total_amount + inv2.total_amount + inv3.total_amount)
        assert total_paid == 150.0  # 120 + 30

        # ------------------------------------------------------------
        # 13. Optional: classroom-level aggregation present
        # ------------------------------------------------------------
        if "collection_by_classroom" in report:
            classroom_reports = report["collection_by_classroom"]
            assert any(cr["classroom_id"] == classroom.id for cr in classroom_reports)
