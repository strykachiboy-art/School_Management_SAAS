from enum import Enum


class OnboardingStep(str, Enum):
    SCHOOL_INFO = "school_info"
    LOCALIZATION = "localization"
    ACADEMIC_STRUCTURE = "academic_structure"
    GRADING_CONFIG = "grading_config"
    PROMOTION_CONFIG = "promotion_config"
    ADMIN_ACCOUNT = "admin_account"
    REVIEW = "review"
    DONE = "done"