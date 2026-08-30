from school_app.extensions import ma
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from school_app.models.user import User

class ProfileSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        exclude = ("password", )

