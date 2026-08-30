# App/models/user.py

from school_app.extensions import db
from school_app.enums.role import Role

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=True)  # Nullable for OAuth users
    role = db.Column(db.String(50), nullable=False, default=Role.STUDENT)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=True)
    
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    
    password_reset_token = db.relationship("PasswordResetToken", 
                                           back_populates="user", 
                                           cascade="all, delete-orphan")
    
    student_profile = db.relationship("Student", back_populates="user", uselist=False)
    teacher_profile = db.relationship("Teacher", back_populates="user", uselist=False)
    audit_logs = db.relationship("AuditLog", back_populates="actor", lazy="dynamic")

    @property
    def is_platform_admin(self) -> bool:
        """
        Determines whether the user possesses global platform administrator privileges.
        Platform admins must not be locked to a single school tenant (school_id is None)
        and must hold elevated admin permissions.
        """
        platform_role = getattr(Role, "PLATFORM_ADMIN", Role.ADMIN)
        return self.school_id is None and self.role in (platform_role, Role.ADMIN)