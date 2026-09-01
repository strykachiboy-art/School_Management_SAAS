import pytest

from school_app.modules.academics.services.academic_stage_service import (
    create_academic_stage,
)
from school_app.modules.academics.services.academic_level_service import (
    create_academic_level,
)
from school_app.modules.academics.services.section_service import (
    create_section,
    get_all_sections,
    get_section,
    update_section,
    delete_section,
)


class DummyData:
    def __init__(
        self,
        name,
        level_id=None,
        stage_id=None,
        display_order=1,
        is_active=True,
    ):
        self.name = name
        self.level_id = level_id
        self.stage_id = stage_id
        self.display_order = display_order
        self.is_active = is_active


def test_full_section_service(app, school, admin_actor_id):
    with app.app_context():
        # --------------------------------------------------------------
        # Setup parent stage and level
        # --------------------------------------------------------------
        stage = create_academic_stage(
            DummyData(
                name="Senior Secondary",
                display_order=1,
            ),
            actor_id=admin_actor_id,
        )

        level = create_academic_level(
            DummyData(
                name="SS1",
                stage_id=stage.id,
                display_order=1,
            ),
            actor_id=admin_actor_id,
        )

        # --------------------------------------------------------------
        # 1. Test create_section
        # --------------------------------------------------------------
        data = DummyData(
            name="Science",
            level_id=level.id,
            display_order=1,
        )

        section = create_section(
            data,
            actor_id=admin_actor_id,
        )

        assert section.id is not None
        assert section.name == "Science"
        assert section.level_id == level.id
        assert section.school_id == school.id

        # --------------------------------------------------------------
        # 2. Test get_section (single)
        # --------------------------------------------------------------
        fetched_section = get_section(
            section.id,
            school_id=school.id,
        )

        assert fetched_section is not None
        assert fetched_section.name == "Science"
        assert fetched_section.school_id == school.id

        # --------------------------------------------------------------
        # 3. Test get_all_sections (with filters)
        # --------------------------------------------------------------
        pagination_result = get_all_sections(
            level_id=level.id,
            search="Science",
            page=1,
            per_page=10,
            school_id=school.id,
        )

        assert pagination_result.total == 1
        assert len(pagination_result.items) == 1
        assert pagination_result.items[0].name == "Science"
        assert pagination_result.items[0].school_id == school.id

        # --------------------------------------------------------------
        # 4. Test update_section
        # --------------------------------------------------------------
        update_data = DummyData(
            name="Science Updated",
            level_id=level.id,
            display_order=2,
            is_active=True,
        )

        updated_section = update_section(
            update_data,
            section.id,
            actor_id=admin_actor_id,
        )

        assert updated_section is not None
        assert updated_section.name == "Science Updated"
        assert updated_section.display_order == 2
        assert updated_section.is_active is True
        assert updated_section.school_id == school.id

        # --------------------------------------------------------------
        # 5. Test delete_section
        # --------------------------------------------------------------
        deleted = delete_section(
            section.id,
            actor_id=admin_actor_id,
        )

        assert deleted is True

        # Verify it's gone
        assert get_section(
            section.id,
            school_id=school.id,
        ) is None


def test_service_level_not_found_handling(
    app,
    admin_actor_id,
):
    """Creating a section with a non-existent level_id should abort with 404."""
    with app.app_context():
        data = DummyData(
            name="Orphan Section",
            level_id=99999,
        )

        with pytest.raises(Exception):
            create_section(
                data,
                actor_id=admin_actor_id,
            )