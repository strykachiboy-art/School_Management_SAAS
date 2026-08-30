from school_app.extensions import db
from school_app.utils.password import hash_password, verify_password


def change_password(user, current_password, new_password):

    if not verify_password(current_password, user.password):
        raise ValueError("Current password is incorrect")

    if verify_password(new_password, user.password):
        raise ValueError("New password must be different from the current password")

    user.password = hash_password(new_password)

    db.session.commit()

    return user