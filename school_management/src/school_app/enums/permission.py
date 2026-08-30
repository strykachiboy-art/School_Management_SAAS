from enum import Enum

class Permission(str, Enum):

    MARK_ATTENDANCE = "mark_attendance"
    ENTER_GRADES = "enter_grades"
    UPDATE_GRADES = "update_grades"
    VIEW_TIMETABLE = "view_timetable"
    VIEW_RESULTS = "view_results"
    MANAGE_TEACHERS = "manage_teachers"