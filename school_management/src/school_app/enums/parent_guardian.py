from enum import Enum

class ParentGuardianEnum(str, Enum):
    FATHER = "FATHER"
    MOTHER = "MOTHER"
    GUARDIAN = "GUARDIAN"
    OTHER = "OTHER"