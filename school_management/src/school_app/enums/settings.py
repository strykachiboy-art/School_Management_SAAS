from enum import Enum


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"