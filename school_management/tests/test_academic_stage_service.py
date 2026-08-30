import pytest
from src.school_app.modules.academics.services.academic_stage_service import (
    create_academic_stage,
    get_all_academic_stages,
    get_academic_stage,
    update_academic_stage,
    delete_academic_stage
)

class DummyData:
    def __init__(self, name, display_order=1, is_active=True):
        self.name = name
        self.display_order = display_order
        self.is_active = is_active

def test_full_academic_stage_service(app):
    with app.app_context():
        # 1. Test create_academic_stage
        data = DummyData(name="Junior Secondary", display_order=1)
        stage = create_academic_stage(data, actor_id=1)
        assert stage.id is not None
        assert stage.name == "Junior Secondary"

        # 2. Test get_academic_stage (single)
        fetched_stage = get_academic_stage(stage.id)
        assert fetched_stage is not None
        assert fetched_stage.name == "Junior Secondary"

        # 3. Test get_all_academic_stages
        pagination_result = get_all_academic_stages(search="Junior", page=1, per_page=10)
        assert pagination_result.total == 1
        assert pagination_result.items[0].name == "Junior Secondary"

        # 4. Test update_academic_stage
        update_data = DummyData(name="Senior Secondary", display_order=2, is_active=True)
        updated_stage = update_academic_stage(update_data, stage.id, actor_id=1)
        assert updated_stage.name == "Senior Secondary"
        assert updated_stage.display_order == 2

        # 5. Test delete_academic_stage
        deleted = delete_academic_stage(stage.id, actor_id=1)
        assert deleted is True
        
        # Verify it's gone
        assert get_academic_stage(stage.id) is None

def test_service_duplicate_name_handling(app):
    """Test that creating stages with duplicate names triggers an integrity error abort."""
    with app.app_context():
        data1 = DummyData(name="Primary", display_order=1)
        create_academic_stage(data1, actor_id=1)

        data2 = DummyData(name="Primary", display_order=2)
        with pytest.raises(Exception):  # Flask aborts with 400
            create_academic_stage(data2, actor_id=1)