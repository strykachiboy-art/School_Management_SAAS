from enum import Enum


class GradingStrategy(str, Enum):
    PERCENTAGE = "percentage"
    LETTER_GRADE = "letter_grade"
    GPA = "gpa"
    PASS_FAIL = "pass_fail"
    CUSTOM = "custom"