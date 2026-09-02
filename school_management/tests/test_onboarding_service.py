from school_app.enums.onboarding import OnboardingStep
from school_app.extensions import db
from school_app.models.academic_level import AcademicLevel
from school_app.models.academic_stage import AcademicStage
from school_app.models.section import Section
from school_app.modules.onboarding.requests.onboarding_request import AcademicStructureStepRequest
from school_app.modules.onboarding.services.onboarding_service import submit_academic_structure


class Payload:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_submit_academic_structure_is_idempotent(app, school, admin_actor_id):
    with app.app_context():
        payload = AcademicStructureStepRequest(
            stages=[
                {
                    "name": "Primary",
                    "code": "P",
                    "display_order": 1,
                    "levels": [
                        {
                            "name": "Grade 1",
                            "display_order": 0,
                            "sections": ["A", "B"],
                        }
                    ],
                }
            ]
        )

        first = submit_academic_structure(school.id, payload, admin_actor_id)
        second = submit_academic_structure(school.id, payload, admin_actor_id)

        stages = db.session.scalars(db.select(AcademicStage).filter_by(school_id=school.id)).all()
        levels = db.session.scalars(db.select(AcademicLevel).filter_by(school_id=school.id)).all()
        sections = db.session.scalars(db.select(Section).filter_by(school_id=school.id)).all()

        assert len(stages) == 1
        assert len(levels) == 1
        assert len(sections) == 2
        assert first.completed_steps == second.completed_steps
        assert OnboardingStep.ACADEMIC_STRUCTURE.value in second.completed_steps
        assert second.current_step == OnboardingStep.GRADING_CONFIG
