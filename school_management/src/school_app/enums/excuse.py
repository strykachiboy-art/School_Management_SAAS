from enum import Enum

class ExcuseStatus(str, Enum):
    
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"