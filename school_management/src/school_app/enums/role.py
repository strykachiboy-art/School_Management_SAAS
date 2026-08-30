from enum import Enum

class Role(str, Enum):
    PLATFORM_ADMIN = "platform_admin"
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"
    HEAD_TEACHER = "head_teacher"
    PRINCIPAL = "principal"