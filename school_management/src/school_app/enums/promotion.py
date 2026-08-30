from enum import Enum

class PromotionDecision(str, Enum):
    
    PROMOTED = "promoted"
    REPEATED = "repeated"
    GRADUATED = "graduated"