import pytest

from school_app.modules.grading.services.grade_service import (
    calculate_total,
    calculate_overall_average,
    calculate_grade,
    calculate_remark,
    calculate_student_grade,
)


# ----------------------------------------------------------------------
# Fake objects
# ----------------------------------------------------------------------

class FakeExam:
    def __init__(
        self,
        subject_id=1,
        weight=1.0,
        total_marks=100,
    ):
        self.subject_id = subject_id
        self.weight = weight
        self.total_marks = total_marks


class FakeResult:
    """
    Lightweight stand-in for Result.

    These tests exercise the grading service without requiring a database.
    """

    def __init__(
        self,
        marks_obtained,
        subject_id=1,
        weight=1.0,
        total_marks=100,
    ):
        self.marks_obtained = marks_obtained
        self.exam = FakeExam(
            subject_id=subject_id,
            weight=weight,
            total_marks=total_marks,
        )


# ======================================================================
# calculate_total
# ======================================================================

def test_calculate_total_sums_marks():
    results = [
        FakeResult(70),
        FakeResult(50),
        FakeResult(80),
    ]

    assert calculate_total(results) == 200


def test_calculate_total_empty_list():
    assert calculate_total([]) == 0


def test_calculate_total_preserves_decimal_marks():
    results = [
        FakeResult(75.5),
        FakeResult(64.5),
    ]

    assert calculate_total(results) == pytest.approx(140.0)


# ======================================================================
# calculate_overall_average
# ======================================================================

def test_calculate_overall_average_normal():
    results = [
        FakeResult(marks_obtained=80, subject_id=1),
        FakeResult(marks_obtained=60, subject_id=2),
    ]

    assert calculate_overall_average(results) == pytest.approx(70.0)


def test_calculate_overall_average_empty_results_returns_zero():
    assert calculate_overall_average([]) == 0.0


def test_calculate_overall_average_multiple_results():
    results = [
        FakeResult(90, subject_id=1),
        FakeResult(80, subject_id=2),
        FakeResult(70, subject_id=3),
        FakeResult(60, subject_id=4),
    ]

    assert calculate_overall_average(results) == pytest.approx(75.0)


def test_calculate_overall_average_with_decimal_marks():
    results = [
        FakeResult(82.5, subject_id=1),
        FakeResult(77.5, subject_id=2),
    ]

    assert calculate_overall_average(results) == pytest.approx(80.0)


# ======================================================================
# calculate_grade
# ======================================================================

@pytest.mark.parametrize(
    "average,expected",
    [
        (100, "A"),
        (90, "A"),
        (70, "A"),

        (69.9, "B"),
        (60, "B"),

        (59.9, "C"),
        (50, "C"),

        (49.9, "D"),
        (45, "D"),

        (44.9, "E"),
        (40, "E"),

        (39.9, "F"),
        (0, "F"),
        (-5, "F"),
    ],
)
def test_calculate_grade_boundaries(average, expected):
    assert calculate_grade(average) == expected


def test_calculate_grade_above_100():
    """
    The grading function should still classify an average above 100
    as an A rather than failing.
    """
    assert calculate_grade(105) == "A"


# ======================================================================
# calculate_remark
# ======================================================================

@pytest.mark.parametrize(
    "grade,expected_remark",
    [
        ("A", "Excellent"),
        ("B", "Very Good"),
        ("C", "Good"),
        ("D", "Pass"),
        ("E", "Weak Pass"),
        ("F", "Fail"),
    ],
)
def test_calculate_remark_known_grades(grade, expected_remark):
    assert calculate_remark(grade) == expected_remark


def test_calculate_remark_unknown_grade_falls_back():
    assert calculate_remark("Z") == "unknown"


def test_calculate_remark_lowercase_grade():
    """
    If the service normalizes grade input, lowercase grades should resolve
    to the same remarks.
    """
    assert calculate_remark("a") == "Excellent"


# ======================================================================
# calculate_student_grade
# ======================================================================

def test_calculate_student_grade_full_shape():
    results = [
        FakeResult(90, subject_id=1),
        FakeResult(80, subject_id=2),
        FakeResult(70, subject_id=3),
    ]

    result = calculate_student_grade(results)

    assert result["average"] == pytest.approx(80.0)
    assert result["grade"] == "A"
    assert result["remark"] == "Excellent"
    assert set(result.keys()) == {
        "average",
        "grade",
        "remark",
    }


def test_calculate_student_grade_empty_results():
    """
    No results -> average 0 -> grade F -> Fail.
    """

    result = calculate_student_grade([])

    assert result["average"] == 0.0
    assert result["grade"] == "F"
    assert result["remark"] == "Fail"
    assert set(result.keys()) == {
        "average",
        "grade",
        "remark",
    }


def test_calculate_student_grade_average_boundary():
    results = [
        FakeResult(70, subject_id=1),
        FakeResult(70, subject_id=2),
    ]

    result = calculate_student_grade(results)

    assert result["average"] == pytest.approx(70.0)
    assert result["grade"] == "A"
    assert result["remark"] == "Excellent"


def test_calculate_student_grade_below_a_boundary():
    results = [
        FakeResult(69, subject_id=1),
        FakeResult(70, subject_id=2),
    ]

    result = calculate_student_grade(results)

    assert result["average"] == pytest.approx(69.5)
    assert result["grade"] == "B"
    assert result["remark"] == "Very Good"


# ======================================================================
# Weight handling
# ======================================================================

def test_calculate_overall_average_uses_equal_average_for_default_weights():
    results = [
        FakeResult(80, subject_id=1, weight=1.0),
        FakeResult(60, subject_id=2, weight=1.0),
    ]

    assert calculate_overall_average(results) == pytest.approx(70.0)


def test_calculate_overall_average_weighted_results():
    """
    Higher-weighted results should have a greater influence on the
    overall average if the service supports exam weighting.
    """
    results = [
        FakeResult(80, subject_id=1, weight=2.0),
        FakeResult(60, subject_id=2, weight=1.0),
    ]

    expected = (80 * 2 + 60 * 1) / (2 + 1)

    assert calculate_overall_average(results) == pytest.approx(expected)