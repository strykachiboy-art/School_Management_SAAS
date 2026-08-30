from enum import Enum

class ReportCardStatus(str, Enum):
    DRAFT = "Draft"
    CALCULATED = "Calculated"
    REVIEWED = "Reviewed"
    APPROVED = "Approved"
    PUBLISHED = "Published"
    UNPUBLISHED = "Unpublished"
    ARCHIVED = "Archived"