from enum import Enum


class EnrollmentStatus(str, Enum):
    ACTIVE = "active"          
    TRANSFERRED = "transferred" 
    PROMOTED = "promoted"      
    REPEATED = "repeated"   
    WITHDRAWN = "withdrawn"   
    GRADUATED = "graduated"    