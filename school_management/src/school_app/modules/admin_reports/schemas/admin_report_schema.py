from marshmallow import schema, fields

class AdminReportSchema(schema):
    # school overview
    total_students = fields.Integer(dump_only=True)
    total_teachers = fields.Integer(dump_only=True)
    total_classrooms = fields.Integer(dump_only=True)
    total_exams = fields.Integer(dump_only=True)
    total_subjects = fields.Integer(dump_only=True)
    
    # Student Statistics
    active_students = fields.Integer(dump_only=True)
    students_per_classroom = fields.Dict(
        keys=fields.Str(),
        values=fields.Integer()
    )
    
    # Academic statistics
    average_score = fields.Float(dump_only=True)
    highest_score = fields.Float(dump_only=True)
    lowest_score = fields.Float(dump_only=True)
    pass_count = fields.Integer(dump_only=True)
    fail_count = fields.Integer(dump_only=True)
    
    grade_distribution = fields.Dict(
        keys=fields.Str(),
        values=fields.Integer()
    )