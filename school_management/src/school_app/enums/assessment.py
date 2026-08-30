from enum import Enum


class AssessmentType(str, Enum):
    ASSIGNMENT = "assignment"
    HOMEWORK = "homework"
    QUIZ = "quiz"
    CLASS_TEST = "class_test"
    UNIT_TEST = "unit_test"
    MID_TERM_TEST = "mid_term_test"
    CONTINUOUS_ASSESSMENT = "continuous_assessment"
    PRACTICAL = "practical"
    LABORATORY_WORK = "laboratory_work"
    PROJECT = "project"
    COURSEWORK = "coursework"
    PRESENTATION = "presentation"
    ORAL_ASSESSMENT = "oral_assessment"
    PARTICIPATION = "participation"
    EXAMINATION = "examination"  # default — matches pre-existing Exam rows
    CUSTOM = "custom"