# tests/test_admin_report_fees_detailed.py

from datetime import date
from decimal import Decimal

from school_app.models.academic_session import AcademicSession
from school_app.models.term import Term
from school_app.models.classroom import Classroom
from school_app.models.school_fees import Invoice, Payment
from school_app.enums.school_fees import (
    PaymentStatus,
    PaymentMethod,
    PaymentGateway,
)

from school_app.modules.admin_reports.services.admin_report_fees_service import (
    get_admin_report_fees,
)


def test_get_admin_report_fees_comprehensive(app, db_session, school, make_student):
    """
    Test the admin fee report across:

    - expected invoice totals
    - confirmed payments
    - outstanding balances
    - fully paid students
    - partially paid students
    - unpaid students
    - pending gateway payments
    - failed gateway payments
    - payment-method breakdown
    - classroom collection breakdown
    - session collection breakdown
    - term collection breakdown
    """
    with app.app_context():
        # ------------------------------------------------------------
        # 1. Use the existing school fixture (do not create another School)
        # ------------------------------------------------------------

        # ------------------------------------------------------------
        # 2. Academic session
        # ------------------------------------------------------------
        academic_session = AcademicSession(
            school_id=school.id,
            name="2025/2026",
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
        )
        db_session.add(academic_session)
        db_session.flush()

        # ------------------------------------------------------------
        # 3. Term
        # ------------------------------------------------------------
        term = Term(
            school_id=school.id,
            academic_session_id=academic_session.id,
            name="First Term",
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 15),
        )
        db_session.add(term)
        db_session.flush()

        # ------------------------------------------------------------
        # 4. Classroom
        # ------------------------------------------------------------
        classroom = Classroom(
            school_id=school.id,
            name="Grade 10",
            capacity=30,
        )
        db_session.add(classroom)
        db_session.flush()

        # ------------------------------------------------------------
        # 5. Students
        # ------------------------------------------------------------
        # Use the project fixture because Student.user_id is NOT NULL.
        student1 = make_student("fees_alice")
        student2 = make_student("fees_bob")
        student3 = make_student("fees_charlie")

        # Merge into session and attach to classroom
        student1 = db_session.merge(student1)
        student2 = db_session.merge(student2)
        student3 = db_session.merge(student3)

        student1.classroom_id = classroom.id
        student2.classroom_id = classroom.id
        student3.classroom_id = classroom.id

        db_session.flush()

        # ------------------------------------------------------------
        # 6. Invoices
        # ------------------------------------------------------------
        inv1 = Invoice(
            school_id=school.id,
            student_id=student1.id,
            session_id=academic_session.id,
            term_id=term.id,
            total_amount=Decimal("100.00"),
        )

        inv2 = Invoice(
            school_id=school.id,
            student_id=student2.id,
            session_id=academic_session.id,
            term_id=term.id,
            total_amount=Decimal("200.00"),
        )

        inv3 = Invoice(
            school_id=school.id,
            student_id=student3.id,
            session_id=academic_session.id,
            term_id=term.id,
            total_amount=Decimal("150.00"),
        )

        db_session.add_all([inv1, inv2, inv3])
        db_session.flush()

        # ------------------------------------------------------------
        # 7. Payments
        # ------------------------------------------------------------
        # Alice: fully paid (confirmed)
        payment_confirmed = Payment(
            school_id=school.id,
            invoice_id=inv1.id,
            student_id=student1.id,
            amount=Decimal("100.00"),
            status=PaymentStatus.CONFIRMED,
            payment_method=PaymentMethod.CASH,
            reference="PAY-001",
        )

        # Bob: partially paid (confirmed)
        payment_part = Payment(
            school_id=school.id,
            invoice_id=inv2.id,
            student_id=student2.id,
            amount=Decimal("50.00"),
            status=PaymentStatus.CONFIRMED,
            payment_method=PaymentMethod.BANK_TRANSFER,
            reference="PAY-002",
        )

        # Bob: pending gateway payment (should not count as confirmed)
        payment_pending = Payment(
            school_id=school.id,
            invoice_id=inv2.id,
            student_id=student2.id,
            amount=Decimal("75.00"),
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.BANK_TRANSFER,
            gateway=PaymentGateway.STRIPE,
            reference="PAY-003",
        )

        # Charlie: failed gateway payment (still unpaid)
        payment_failed = Payment(
            school_id=school.id,
            invoice_id=inv3.id,
            student_id=student3.id,
            amount=Decimal("150.00"),
            status=PaymentStatus.FAILED,
            payment_method=PaymentMethod.BANK_TRANSFER,
            gateway=PaymentGateway.PAYSTACK,
            reference="PAY-004",
        )

        db_session.add_all(
            [payment_confirmed, payment_part, payment_pending, payment_failed]
        )
        db_session.commit()

        # ------------------------------------------------------------
        # 8. Generate report
        # ------------------------------------------------------------
        report = get_admin_report_fees(session_id=academic_session.id, term_id=term.id)

        # ------------------------------------------------------------
        # 9. Overall financial totals
        # ------------------------------------------------------------
        # 100 + 200 + 150 = 450
        assert report["total_expected"] == 450.0

        # Only confirmed payments: 100 + 50 = 150
        assert report["total_paid"] == 150.0

        # Outstanding: 450 - 150 = 300
        assert report["total_outstanding"] == 300.0

        # Only confirmed payment rows
        assert report["payment_count"] == 2

        # ------------------------------------------------------------
        # 10. Student status
        # ------------------------------------------------------------
        assert report["fully_paid_students"] == 1
        assert report["partially_paid_students"] == 1
        assert report["unpaid_students"] == 1

        # ------------------------------------------------------------
        # 11. Collection rate
        # ------------------------------------------------------------
        # 150 / 450 * 100 = 33.3%
        assert report["collection_rate"] == 33.3

        # ------------------------------------------------------------
        # 12. Payment-method breakdown
        # ------------------------------------------------------------
        # Keys are normalized to strings in the service; check both lowercase and enum value possibilities
        # Prefer the normalized string keys produced by the service.
        assert report["collection_by_payment_method"].get("CASH", report["collection_by_payment_method"].get("cash")) == 100.0
        assert report["collection_by_payment_method"].get("BANK_TRANSFER", report["collection_by_payment_method"].get("bank_transfer")) == 50.0

        # ------------------------------------------------------------
        # 13. Pending gateway payments
        # ------------------------------------------------------------
        assert report["pending_gateway_payments"]["count"] == 1
        assert report["pending_gateway_payments"]["total_amount"] == 75.0

        # ------------------------------------------------------------
        # 14. Failed gateway payments
        # ------------------------------------------------------------
        assert report["failed_gateway_payments"]["count"] == 1
        assert report["failed_gateway_payments"]["total_amount"] == 150.0

        # ------------------------------------------------------------
        # 15. Classroom breakdown
        # ------------------------------------------------------------
        assert len(report["collection_by_classroom"]) == 1
        classroom_report = report["collection_by_classroom"][0]
        assert classroom_report["classroom_id"] == classroom.id
        assert classroom_report["classroom_name"] == "Grade 10"
        assert classroom_report["total_expected"] == 450.0
        assert classroom_report["total_paid"] == 150.0

        # ------------------------------------------------------------
        # 16. Session breakdown
        # ------------------------------------------------------------
        assert len(report["collection_by_session"]) == 1
        session_report = report["collection_by_session"][0]
        assert session_report["session_id"] == academic_session.id
        assert session_report["session_name"] == "2025/2026"
        assert session_report["total_expected"] == 450.0
        assert session_report["total_paid"] == 150.0

        # ------------------------------------------------------------
        # 17. Term breakdown
        # ------------------------------------------------------------
        assert len(report["collection_by_term"]) == 1
        term_report = report["collection_by_term"][0]
        assert term_report["term_id"] == term.id
        assert term_report["term_name"] == "First Term"
        assert term_report["total_expected"] == 450.0
        assert term_report["total_paid"] == 150.0
