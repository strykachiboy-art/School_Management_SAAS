from enum import Enum

class NotificationType(str, Enum):
    GENERAL = "GENERAL"
    ATTENDANCE = "ATTENDANCE"
    EXCUSE = "EXCUSE"
    RESULT = "RESULT"
    EXAM = "EXAM"
    TIMETABLE = "TIMETABLE"
    PROMOTION = "PROMOTION"
    SCHOOL_FEES = "SCHOOL_FEES"
    SYSTEM = "SYSTEM"