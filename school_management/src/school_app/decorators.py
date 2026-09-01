# App/decorators.py

"""Reusable decorators for the application."""
from functools import wraps
from flask import abort, current_app, g, jsonify
from school_app.enums.role import Role
from school_app.enums.permission import Permission


def role_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not g.user:
                abort(401, description="Authentication required")
            
            # Extract string value if role is an Enum
            user_role = g.user.role.value if hasattr(g.user.role, "value") else str(g.user.role)
            allowed = [r.value if hasattr(r, "value") else str(r) for r in allowed_roles]
            
            if user_role.lower() not in [a.lower() for a in allowed]:
                abort(403, description="Permission denied")
                
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def platform_admin_required(fn):
    """
    Decorator enforcing platform administrator privileges.
    Ensures the user is authenticated and possesses platform-level admin rights.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not g.user:
            abort(401, description="Authentication required")
        
        is_platform_admin = getattr(g.user, "is_platform_admin", False)
        user_role = g.user.role.value if hasattr(g.user.role, "value") else str(g.user.role)
        
        if not (is_platform_admin or user_role.lower() == Role.PLATFORM_ADMIN.value):
            abort(403, description="Platform Administrator access required")
            
        return fn(*args, **kwargs)
    return wrapper


def permission_required(*required_permissions):
    """
    Checks that the logged-in teacher has been assigned ALL of the given
    permissions before allowing the route through. Admins and Platform Admins
    always bypass permission checks entirely.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not g.user:
                abort(401, description="Authentication required")

            user_role = (
                g.user.role.value
                if hasattr(g.user.role, "value")
                else str(g.user.role)
            )

            # Admins and Platform Admins bypass permission checks entirely.
            if user_role.lower() in (
                Role.ADMIN.value,
                Role.PLATFORM_ADMIN.value,
            ):
                return fn(*args, **kwargs)

            teacher = getattr(g.user, "teacher_profile", None)

            if teacher is None:
                abort(403, description="Teacher profile not found")

            from school_app.models.teacher_permission import TeacherPermission

            granted = {
                p.permission.value
                if hasattr(p.permission, "value")
                else p.permission
                for p in TeacherPermission.query.filter_by(
                    teacher_id=teacher.id
                ).all()
            }

            required = [
                p.value if hasattr(p, "value") else str(p)
                for p in required_permissions
            ]

            missing = [p for p in required if p not in granted]

            if missing:
                abort(
                    403,
                    description=f"Missing permission(s): {', '.join(missing)}",
                )

            return fn(*args, **kwargs)
        return wrapper
    return decorator
