import pytest

JSON_HEADERS = {"Accept": "application/json"}

from school_app.modules.grading.services.grade_service import (
    calculate_total,
    calculate_average,
    calculate_grade,
    calculate_remark,
    calculate_student_grade,
)


class FakeResult:
    """Lightweight stand-in so these tests don't need real Result/DB objects."""
    def __init__(self, marks_obtained):
        self.marks_obtained = marks_obtained


# ---------------------- calculate_total ----------------------

def test_calculate_total_sums_marks():
    results = [FakeResult(70), FakeResult(50), FakeResult(80)]
    assert calculate_total(results) == 200


def test_calculate_total_empty_list():
    assert calculate_total([]) == 0


# ---------------------- calculate_average ----------------------

def test_calculate_average_normal():
    assert calculate_average(200, 4) == 50


def test_calculate_average_zero_subjects_returns_zero():
    # guards the ZeroDivisionError
    assert calculate_average(0, 0) == 0


# ---------------------- calculate_grade ----------------------

@pytest.mark.parametrize("average,expected", [
    (100, "A"),
    (70, "A"),    # boundary: exactly at threshold
    (69.9, "B"),
    (60, "B"),
    (59, "C"),
    (50, "C"),
    (45, "D"),
    (44, "E"),
    (40, "E"),
    (39, "F"),
    (0, "F"),
    (-5, "F"),    # below all thresholds
])
def test_calculate_grade_boundaries(average, expected):
    assert calculate_grade(average) == expected


# ---------------------- calculate_remark ----------------------

@pytest.mark.parametrize("grade,expected_remark", [
    ("A", "Excelent"),  # NOTE: matches the typo in GRADE_REMARK — see caveat below
    ("B", "Very Good"),
    ("C", "Good"),
    ("D", "Pass"),
    ("E", "Weak Pass"),
    ("F", "Fail"),
])
def test_calculate_remark_known_grades(grade, expected_remark):
    assert calculate_remark(grade) == expected_remark


def test_calculate_remark_unknown_grade_falls_back():
    assert calculate_remark("Z") == "unknown"


# ---------------------- calculate_student_grade (integration of the above) ----------------------

def test_calculate_student_grade_full_shape():
    results = [FakeResult(90), FakeResult(80), FakeResult(70)]
    result = calculate_student_grade(results)

    assert result["total"] == 240
    assert result["average"] == pytest.approx(80.0)
    assert result["grade"] == "A"
    assert result["remark"] == "Excelent"
    assert set(result.keys()) == {"total", "average", "grade", "remark"}


def test_calculate_student_grade_empty_results():
    # no exam results at all -> average defaults to 0 -> grade F
    result = calculate_student_grade([])
    assert result["total"] == 0
    assert result["average"] == 0
    assert result["grade"] == "F"
    assert result["remark"] == "Fail"