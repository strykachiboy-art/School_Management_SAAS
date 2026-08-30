import pytest

from school_app.modules.grading.services.grade_service import (
    calculate_total,
    calculate_overall_average,
    calculate_grade,
    calculate_remark,
    calculate_student_grade,
)


class FakeExam:
    def __init__(self, subject_id=1, weight=1.0, total_marks=100):
        self.subject_id = subject_id
        self.weight = weight
        self.total_marks = total_marks


class FakeResult:
    """Lightweight stand-in so these tests don't need real Result/DB objects."""
    def __init__(self, marks_obtained, subject_id=1, weight=1.0, total_marks=100):
        self.marks_obtained = marks_obtained
        self.exam = FakeExam(subject_id=subject_id, weight=weight, total_marks=total_marks)


# ---------------------- calculate_total ----------------------

def test_calculate_total_sums_marks():
    results = [FakeResult(70), FakeResult(50), FakeResult(80)]
    assert calculate_total(results) == 200


def test_calculate_total_empty_list():
    assert calculate_total([]) == 0


# ---------------------- calculate_overall_average ----------------------

def test_calculate_overall_average_normal():
    results = [
        FakeResult(marks_obtained=80, subject_id=1),
        FakeResult(marks_obtained=60, subject_id=2),
    ]
    assert calculate_overall_average(results) == 70.0


def test_calculate_overall_average_empty_results_returns_zero():
    assert calculate_overall_average([]) == 0.0


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
    ("A", "Excellent"),
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


# ---------------------- calculate_student_grade ----------------------

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
    assert set(result.keys()) == {"average", "grade", "remark"}


def test_calculate_student_grade_empty_results():
    # no exam results at all -> average defaults to 0 -> grade F
    result = calculate_student_grade([])
    assert result["average"] == 0.0
    assert result["grade"] == "F"
    assert result["remark"] == "Fail"
    assert set(result.keys()) == {"average", "grade", "remark"}