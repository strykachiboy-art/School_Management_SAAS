from school_app.extensions import db
from school_app.models.classroom import Classroom
from school_app.models.academic_stage import AcademicStage
from school_app.models.academic_level import AcademicLevel
from school_app.models.section import Section
from school_app.modules.classrooms.services.backfill_service import (
    backfill_classroom_sections,
)


def test_backfill_classroom_sections_assigns_default_section(
    app, school
):
    with app.app_context():
        classroom = Classroom(
            name="JSS 1",
            level=1,
            section_id=None,
        )
        db.session.add(classroom)
        db.session.commit()

        result = backfill_classroom_sections()

        db.session.refresh(classroom)

        assert result["dry_run"] is False
        assert len(result["backfilled"]) == 1
        assert result["skipped"] == []
        assert "Level 1" in result["levels_created"]

        assert classroom.section_id is not None

        section = db.session.get(Section, classroom.section_id)

        assert section is not None
        assert section.name == "A"

        level = db.session.get(AcademicLevel, section.level_id)

        assert level is not None
        assert level.name == "Level 1"

        stage = db.session.get(AcademicStage, level.stage_id)

        assert stage is not None
        assert stage.name == "Unspecified Stage (backfilled)"


def test_backfill_classroom_sections_reuses_level_and_section(
    app, school
):
    with app.app_context():
        classroom_one = Classroom(
            name="JSS 1 A",
            level=1,
            section_id=None,
        )

        classroom_two = Classroom(
            name="JSS 1 B",
            level=1,
            section_id=None,
        )

        db.session.add_all([classroom_one, classroom_two])
        db.session.commit()

        result = backfill_classroom_sections()

        db.session.refresh(classroom_one)
        db.session.refresh(classroom_two)

        assert len(result["backfilled"]) == 2

        assert classroom_one.section_id is not None
        assert classroom_two.section_id is not None

        # Same legacy level should reuse the same section.
        assert classroom_one.section_id == classroom_two.section_id

        sections = db.session.scalars(
            db.select(Section)
        ).all()

        assert len(sections) == 1

        levels = db.session.scalars(
            db.select(AcademicLevel)
        ).all()

        assert len(levels) == 1


def test_backfill_classroom_sections_skips_classroom_without_level(
    app, school
):
    with app.app_context():
        classroom = Classroom(
            name="No Level Classroom",
            level=None,
            section_id=None,
        )

        db.session.add(classroom)
        db.session.commit()

        result = backfill_classroom_sections()

        db.session.refresh(classroom)

        assert classroom.section_id is None

        assert result["backfilled"] == []
        assert len(result["skipped"]) == 1

        skipped = result["skipped"][0]

        assert skipped["classroom_id"] == classroom.id
        assert skipped["classroom_name"] == "No Level Classroom"
        assert skipped["reason"] == "no level value to backfill from"


def test_backfill_classroom_sections_dry_run_does_not_modify_database(
    app, school
):
    with app.app_context():
        classroom = Classroom(
            name="JSS 2",
            level=2,
            section_id=None,
        )

        db.session.add(classroom)
        db.session.commit()

        classroom_id = classroom.id

        result = backfill_classroom_sections(dry_run=True)

        db.session.expire_all()

        classroom = db.session.get(Classroom, classroom_id)

        assert result["dry_run"] is True

        assert len(result["backfilled"]) == 1
        assert result["skipped"] == []
        assert "Level 2" in result["levels_created"]

        backfilled = result["backfilled"][0]

        assert backfilled["classroom_id"] == classroom_id
        assert backfilled["classroom_name"] == "JSS 2"
        assert backfilled["old_level"] == 2
        assert (
            backfilled["would_assign_section"]
            == "Unspecified Stage (backfilled) > Level 2 > A"
        )

        # Dry run must not actually assign anything.
        assert classroom.section_id is None

        # Nothing should have been persisted.
        stage = db.session.scalars(
            db.select(AcademicStage).where(
                AcademicStage.name == "Unspecified Stage (backfilled)"
            )
        ).first()

        assert stage is None


def test_backfill_classroom_sections_dry_run_reports_all_classrooms(
    app, school
):
    with app.app_context():
        classroom_one = Classroom(
            name="JSS 1",
            level=1,
            section_id=None,
        )

        classroom_two = Classroom(
            name="JSS 2",
            level=2,
            section_id=None,
        )

        db.session.add_all([classroom_one, classroom_two])
        db.session.commit()

        result = backfill_classroom_sections(dry_run=True)

        assert len(result["backfilled"]) == 2

        classroom_ids = {
            item["classroom_id"]
            for item in result["backfilled"]
        }

        assert classroom_one.id in classroom_ids
        assert classroom_two.id in classroom_ids

        assert "Level 1" in result["levels_created"]
        assert "Level 2" in result["levels_created"]
        
def test_backfill_classroom_sections_ignores_classroom_with_existing_section(
    app, school
):
    with app.app_context():
        stage = AcademicStage(
            name="Existing Stage",
            display_order=1,
        )
        db.session.add(stage)
        db.session.flush()

        level = AcademicLevel(
            stage_id=stage.id,
            name="Level 1",
            display_order=1,
        )
        db.session.add(level)
        db.session.flush()

        section = Section(
            level_id=level.id,
            name="A",
        )
        db.session.add(section)
        db.session.flush()

        classroom = Classroom(
            name="Already Assigned",
            level=1,
            section_id=section.id,
        )
        db.session.add(classroom)
        db.session.commit()

        result = backfill_classroom_sections()

        db.session.refresh(classroom)

        assert result["backfilled"] == []
        assert result["skipped"] == []

        assert classroom.section_id == section.id