from collections import defaultdict

from school_app.extensions import db
from school_app.models.grading_rule import GradingRule
from school_app.models.grading_system import GradingSystem
from school_app.modules.grading.services.grading_system_service import (
    get_default_grading_system,
)


# =========================== calculate total marks =================================
def calculate_total(results):
    """Calculate the sum of marks obtained across a collection of exam results."""
    if not results:
        return 0.0

    return sum(result.marks_obtained for result in results)


# =========================== normalize a single result =================================
def normalize_score(marks_obtained, total_marks):
    """Convert a raw score into a 0-100 percentage of its own maximum."""
    if not total_marks:
        return 0.0

    return (marks_obtained / total_marks) * 100


# =========================== group results by subject =================================
def _group_by_subject(results):
    grouped = defaultdict(list)

    for result in results:
        grouped[result.exam.subject_id].append(result)

    return grouped


# =========================== calculate one subject's score =================================
def calculate_subject_score(results_for_subject):
    """
    Combine every assessment component for a single subject into one
    weighted, normalized score (0-100).
    """
    if not results_for_subject:
        return 0.0

    total_weight = sum(
        getattr(result.exam, "weight", 1.0) or 0.0
        for result in results_for_subject
    )

    if total_weight <= 0:
        return 0.0

    weighted_sum = sum(
        normalize_score(
            result.marks_obtained,
            result.exam.total_marks,
        )
        * (getattr(result.exam, "weight", 1.0) or 0.0)
        for result in results_for_subject
    )

    return weighted_sum / total_weight


# =========================== per-subject scores (public) =================================
def get_subject_scores(results):
    grouped = _group_by_subject(results)

    return {
        subject_id: calculate_subject_score(subject_results)
        for subject_id, subject_results in grouped.items()
    }


# =========================== calculate overall average =================================
def calculate_overall_average(results):
    """
    Calculate the weighted overall average of the supplied results.

    Each result contributes its normalized percentage according to the
    weight of its exam.

    Example:
        80 marks with weight 2
        60 marks with weight 1

        (80 * 2 + 60 * 1) / (2 + 1)
        = 73.3333
    """
    if not results:
        return 0.0

    weighted_sum = 0.0
    total_weight = 0.0

    for result in results:
        weight = getattr(result.exam, "weight", 1.0)

        # Preserve the existing default behavior when weight is missing
        # or explicitly None.
        if weight is None:
            weight = 1.0

        weight = float(weight)

        if weight <= 0:
            continue

        score = normalize_score(
            result.marks_obtained,
            result.exam.total_marks,
        )

        weighted_sum += score * weight
        total_weight += weight

    if total_weight <= 0:
        return 0.0

    return weighted_sum / total_weight


# ============================= calculate grade ==================================
GRADE_SCALE = (
    (70, "A"),
    (60, "B"),
    (50, "C"),
    (45, "D"),
    (40, "E"),
    (0, "F"),
)


def calculate_grade(average, grading_system_id=None, school_id=None):
    from school_app.modules.grading.services.grading_system_service import (
        resolve_grade_for_score,
    )

    grade, _, system_existed = resolve_grade_for_score(
        average,
        grading_system_id=grading_system_id,
        school_id=school_id,
    )

    if grade is not None:
        return grade

    if system_existed:
        return "Ungraded"

    # Only reached if no GradingSystem exists in the DB at all.
    for minimum, fallback_grade in GRADE_SCALE:
        if average >= minimum:
            return fallback_grade

    return "F"


# ====================== Grade Remarks ===========================
GRADE_REMARK = {
    "A": "Excellent",
    "B": "Very Good",
    "C": "Good",
    "D": "Pass",
    "E": "Weak Pass",
    "F": "Fail",
}


def calculate_remark(grade_or_average, grading_system_id=None, school_id=None):

    normalized_grade = (
        str(grade_or_average).strip().upper()
        if grade_or_average is not None
        else ""
    )

    system = (
        db.session.get(GradingSystem, grading_system_id)
        if grading_system_id is not None
        else get_default_grading_system(school_id=school_id)
    )

    if system is not None:
        stmt = db.select(GradingRule).where(
            GradingRule.grading_system_id == system.id,
            GradingRule.grade_name == normalized_grade,
        )

        rule = db.session.scalars(stmt).first()

        if rule is not None and rule.remark is not None:
            return rule.remark

    return GRADE_REMARK.get(normalized_grade, "unknown")


# ===================== calculate student_grade =======================
def calculate_student_grade(results):
    total = calculate_total(results)
    average = calculate_overall_average(results)
    grade = calculate_grade(average)
    remark = calculate_remark(grade)

    return {
        "total": total,
        "average": average,
        "grade": grade,
        "remark": remark,
    }


# ===================== term-level aggregation =======================
def calculate_student_term_grades(student_id: int, term_id: int) -> dict:
    """
    Fetch all exam results for a student in a specific term,
    group by subject, and calculate subject scores, overall average,
    overall grade, and overall remark.
    """
    from school_app.models.result import Result
    from school_app.models.exam import Exam

    # Query all results for the student strictly scoped to exams
    # in the given term.
    results = (
        db.session.query(Result)
        .join(Exam)
        .filter(
            Result.student_id == student_id,
            Exam.term_id == term_id,
        )
        .all()
    )

    if not results:
        return {
            "subject_scores": {},
            "overall_average": 0.0,
            "grade": "N/A",
            "remark": "No results found",
        }

    # Calculate per-subject percentage scores.
    grouped = _group_by_subject(results)
    subject_scores = {}

    for subject_id, subject_results in grouped.items():
        score = calculate_subject_score(subject_results)
        subject_grade = calculate_grade(score)
        subject_remark = calculate_remark(subject_grade)

        subject_scores[str(subject_id)] = {
            "score": round(score, 2),
            "grade": subject_grade,
            "remark": subject_remark,
        }

    overall_avg = calculate_overall_average(results)
    overall_grade = calculate_grade(overall_avg)
    overall_remark = calculate_remark(overall_grade)

    return {
        "subject_scores": subject_scores,
        "overall_average": round(overall_avg, 2),
        "grade": overall_grade,
        "remark": overall_remark,
    }