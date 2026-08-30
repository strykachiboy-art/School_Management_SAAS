from school_app.extensions import db
from school_app.models.classroom import Classroom
from school_app.models.academic_stage import AcademicStage
from school_app.models.academic_level import AcademicLevel
from school_app.models.section import Section


DEFAULT_STAGE_NAME = "Unspecified Stage (backfilled)"
DEFAULT_SECTION_NAME = "A"


def backfill_classroom_sections(dry_run=False):
    """Assigns section_id to every Classroom that has a deprecated `level`
    int but no section_id yet.
    """
    stmt = db.select(Classroom).where(Classroom.section_id.is_(None))
    candidates = db.session.scalars(stmt).all()

    backfilled = []
    skipped = []
    levels_created = []

    if not candidates:
        return {"backfilled": [], "skipped": [], "levels_created": [], "dry_run": dry_run}

    stage = db.session.scalars(
        db.select(AcademicStage).where(AcademicStage.name == DEFAULT_STAGE_NAME)
    ).first()
    if stage is None and not dry_run:
        stage = AcademicStage(name=DEFAULT_STAGE_NAME, display_order=9999)
        db.session.add(stage)
        db.session.flush()

    # Cache of raw level int -> Section, built as we go, so classrooms
    # sharing the same level int reuse the same created Level/Section
    # instead of creating duplicates.
    level_to_section = {}

    for classroom in candidates:
        if classroom.level is None:
            skipped.append({"classroom_id": classroom.id, "classroom_name": classroom.name, "reason": "no level value to backfill from"})
            continue

        raw_level = classroom.level

        if raw_level not in level_to_section:
            level_name = f"Level {raw_level}"
            existing_level = None
            if stage is not None:
                existing_level = db.session.scalars(
                    db.select(AcademicLevel).where(
                        AcademicLevel.stage_id == stage.id, AcademicLevel.name == level_name
                    )
                ).first()

            if existing_level is None:
                if dry_run:
                    # Placeholder only — nothing is actually created in a
                    # dry run. FIX: this branch used to `continue` here,
                    # which skipped straight to the next classroom and
                    # dropped the CURRENT classroom out of the backfilled
                    # report entirely — undercounting the preview by one
                    # for every newly-encountered level. Falls through to
                    # the shared reporting logic below instead now.
                    level_to_section[raw_level] = None
                    levels_created.append(level_name)
                else:
                    academic_level = AcademicLevel(stage_id=stage.id, name=level_name, display_order=raw_level)
                    db.session.add(academic_level)
                    db.session.flush()
                    levels_created.append(level_name)
            else:
                academic_level = existing_level

            if not dry_run:
                section = db.session.scalars(
                    db.select(Section).where(
                        Section.level_id == academic_level.id, Section.name == DEFAULT_SECTION_NAME
                    )
                ).first()
                if section is None:
                    section = Section(level_id=academic_level.id, name=DEFAULT_SECTION_NAME)
                    db.session.add(section)
                    db.session.flush()
                level_to_section[raw_level] = section

        section_for_level = level_to_section.get(raw_level)

        if dry_run:
            backfilled.append({
                "classroom_id": classroom.id,
                "classroom_name": classroom.name,
                "old_level": raw_level,
                "would_assign_section": f"{DEFAULT_STAGE_NAME} > Level {raw_level} > {DEFAULT_SECTION_NAME}",
            })
            continue

        classroom.section_id = section_for_level.id
        backfilled.append({
            "classroom_id": classroom.id,
            "classroom_name": classroom.name,
            "old_level": raw_level,
            "assigned_section_id": section_for_level.id,
        })

    if not dry_run:
        db.session.commit()
    else:
        db.session.rollback()  

    return {
        "backfilled": backfilled,
        "skipped": skipped,
        "levels_created": levels_created,
        "dry_run": dry_run,
    }