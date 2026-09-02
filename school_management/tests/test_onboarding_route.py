import pytest

from school_app.enums.grading import GradingStrategy
from school_app.enums.onboarding import OnboardingStep


# ============================================================================
# SHARED PAYLOADS
# ============================================================================

def academic_structure_payload():
    return {
        "stages": [
            {
                "name": "Primary",
                "code": "PRI",
                "display_order": 1,
                "levels": [
                    {
                        "name": "Primary 1",
                        "display_order": 1,
                        "sections": ["A", "B"],
                    },
                    {
                        "name": "Primary 2",
                        "display_order": 2,
                        "sections": ["A", "B"],
                    },
                ],
            }
        ]
    }


def grading_config_payload():
    # Use the actual enum value rather than assuming that the enum name
    # is also its serialized value.
    strategy = GradingStrategy.LETTER_GRADE.value

    return {
        "name": "Standard Grading",
        "strategy": strategy,
        "rules": [
            {
                "grade_name": "A",
                "min_score": 70,
                "max_score": 100,
                "grade_point": 4.0,
                "remark": "Excellent",
                "display_order": 1,
            },
            {
                "grade_name": "B",
                "min_score": 60,
                "max_score": 69,
                "grade_point": 3.0,
                "remark": "Very Good",
                "display_order": 2,
            },
        ],
    }


def promotion_config_payload():
    return {
        "rules": [
            {
                "name": "Primary 1 to Primary 2",
                "from_level_name": "Primary 1",
                "to_level_name": "Primary 2",
                "min_average_score": 50,
                "min_attendance_percentage": 75,
                "max_failed_subjects": 2,
                "requires_admin_approval": True,
            }
        ]
    }


# ============================================================================
# GET ONBOARDING PROGRESS
# ============================================================================

class TestGetOnboardingProgressRoute:

    def test_get_onboarding_progress_success(
        self,
        client,
        admin_headers,
        school,
    ):
        response = client.get(
            f"/onboarding/{school.id}",
            headers=admin_headers,
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["school_id"] == school.id
        assert "current_step" in data
        assert "completed_steps" in data
        assert "is_completed" in data
        assert "started_at" in data
        assert "completed_at" in data

    def test_get_onboarding_progress_rejects_unauthorized_role(
        self,
        client,
        teacher_headers,
        school,
    ):
        response = client.get(
            f"/onboarding/{school.id}",
            headers=teacher_headers,
        )

        assert response.status_code == 403

    def test_get_onboarding_progress_requires_authentication(
        self,
        client,
        school,
    ):
        response = client.get(
            f"/onboarding/{school.id}",
        )

        assert response.status_code == 401


# ============================================================================
# SCHOOL INFO
# ============================================================================

class TestSubmitSchoolInfoRoute:

    def test_submit_school_info_success(
        self,
        client,
        admin_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/school-info",
            headers=admin_headers,
            json={
                "name": "Updated Test School",
                "slug": "updated-test-school",
                "country": "Nigeria",
            },
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["school_id"] == school.id
        assert "school_info" in data["completed_steps"]

    @pytest.mark.parametrize(
        "payload",
        [
            {"name": "A"},
            {"name": "x" * 201},
            {"slug": "a"},
            {"slug": "x" * 101},
            {"country": "x" * 101},
        ],
    )
    def test_submit_school_info_rejects_invalid_payload(
        self,
        client,
        admin_headers,
        school,
        payload,
    ):
        response = client.post(
            f"/onboarding/{school.id}/school-info",
            headers=admin_headers,
            json=payload,
        )

        assert response.status_code in (400, 422)

    def test_submit_school_info_accepts_empty_payload(
        self,
        client,
        admin_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/school-info",
            headers=admin_headers,
            json={},
        )

        assert response.status_code == 200

    def test_submit_school_info_rejects_teacher(
        self,
        client,
        teacher_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/school-info",
            headers=teacher_headers,
            json={},
        )

        assert response.status_code == 403

    def test_submit_school_info_requires_authentication(
        self,
        client,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/school-info",
            json={},
        )

        assert response.status_code == 401


# ============================================================================
# LOCALIZATION
# ============================================================================

class TestSubmitLocalizationRoute:

    def test_submit_localization_success(
        self,
        client,
        admin_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/localization",
            headers=admin_headers,
            json={
                "timezone": "Africa/Lagos",
                "currency": "NGN",
                "locale": "en-NG",
            },
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["school_id"] == school.id
        assert "localization" in data["completed_steps"]

    @pytest.mark.parametrize(
        "payload",
        [
            {"currency": "NG"},
            {"currency": "x" * 11},
            {"locale": "e"},
            {"locale": "x" * 11},
        ],
    )
    def test_submit_localization_rejects_invalid_payload(
        self,
        client,
        admin_headers,
        school,
        payload,
    ):
        response = client.post(
            f"/onboarding/{school.id}/localization",
            headers=admin_headers,
            json=payload,
        )

        assert response.status_code in (400, 422)

    def test_submit_localization_accepts_empty_payload(
        self,
        client,
        admin_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/localization",
            headers=admin_headers,
            json={},
        )

        assert response.status_code == 200

    def test_submit_localization_rejects_teacher(
        self,
        client,
        teacher_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/localization",
            headers=teacher_headers,
            json={},
        )

        assert response.status_code == 403

    def test_submit_localization_requires_authentication(
        self,
        client,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/localization",
            json={},
        )

        assert response.status_code == 401


# ============================================================================
# ACADEMIC STRUCTURE
# ============================================================================

class TestSubmitAcademicStructureRoute:

    def test_submit_academic_structure_success(
        self,
        client,
        admin_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/academic-structure",
            headers=admin_headers,
            json=academic_structure_payload(),
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["school_id"] == school.id
        assert "academic_structure" in data["completed_steps"]

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"stages": None},
            {"stages": "invalid"},
            {"stages": []},
        ],
    )
    def test_submit_academic_structure_rejects_invalid_payload(
        self,
        client,
        admin_headers,
        school,
        payload,
    ):
        response = client.post(
            f"/onboarding/{school.id}/academic-structure",
            headers=admin_headers,
            json=payload,
        )

        assert response.status_code in (400, 422)

    def test_submit_academic_structure_rejects_invalid_stage_name(
        self,
        client,
        admin_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/academic-structure",
            headers=admin_headers,
            json={
                "stages": [
                    {
                        "name": "",
                        "levels": [],
                    }
                ]
            },
        )

        assert response.status_code in (400, 422)

    def test_submit_academic_structure_rejects_invalid_level_name(
        self,
        client,
        admin_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/academic-structure",
            headers=admin_headers,
            json={
                "stages": [
                    {
                        "name": "Primary",
                        "levels": [
                            {
                                "name": "",
                                "sections": [],
                            }
                        ],
                    }
                ]
            },
        )

        assert response.status_code in (400, 422)

    def test_submit_academic_structure_rejects_teacher(
        self,
        client,
        teacher_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/academic-structure",
            headers=teacher_headers,
            json=academic_structure_payload(),
        )

        assert response.status_code == 403

    def test_submit_academic_structure_requires_authentication(
        self,
        client,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/academic-structure",
            json=academic_structure_payload(),
        )

        assert response.status_code == 401


# ============================================================================
# GRADING CONFIG
# ============================================================================

class TestSubmitGradingConfigRoute:

    def test_submit_grading_config_success(
        self,
        client,
        admin_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/grading-config",
            headers=admin_headers,
            json=grading_config_payload(),
        )

        assert response.status_code == 200, response.get_json()

        data = response.get_json()

        assert data["school_id"] == school.id
        assert "grading_config" in data["completed_steps"]

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"name": ""},
            {
                "name": "Standard Grading",
                "rules": [],
            },
        ],
    )
    def test_submit_grading_config_rejects_invalid_payload(
        self,
        client,
        admin_headers,
        school,
        payload,
    ):
        response = client.post(
            f"/onboarding/{school.id}/grading-config",
            headers=admin_headers,
            json=payload,
        )

        assert response.status_code in (400, 422)

    def test_submit_grading_config_rejects_invalid_rule_grade_name(
        self,
        client,
        admin_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/grading-config",
            headers=admin_headers,
            json={
                "name": "Standard Grading",
                "strategy": GradingStrategy.LETTER_GRADE.value,
                "rules": [
                    {
                        "grade_name": "",
                        "min_score": 70,
                        "max_score": 100,
                    }
                ],
            },
        )

        assert response.status_code in (400, 422)

    def test_submit_grading_config_rejects_teacher(
        self,
        client,
        teacher_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/grading-config",
            headers=teacher_headers,
            json=grading_config_payload(),
        )

        assert response.status_code == 403

    def test_submit_grading_config_requires_authentication(
        self,
        client,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/grading-config",
            json=grading_config_payload(),
        )

        assert response.status_code == 401


# ============================================================================
# PROMOTION CONFIG
# ============================================================================

class TestSubmitPromotionConfigRoute:

    def test_submit_promotion_config_success(
        self,
        client,
        admin_headers,
        school,
    ):
        # The promotion service requires the referenced academic levels
        # to already exist.
        structure_response = client.post(
            f"/onboarding/{school.id}/academic-structure",
            headers=admin_headers,
            json=academic_structure_payload(),
        )

        assert structure_response.status_code == 200

        response = client.post(
            f"/onboarding/{school.id}/promotion-config",
            headers=admin_headers,
            json=promotion_config_payload(),
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["school_id"] == school.id
        assert "promotion_config" in data["completed_steps"]

    def test_submit_promotion_config_accepts_empty_rules(
        self,
        client,
        admin_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/promotion-config",
            headers=admin_headers,
            json={
                "rules": [],
            },
        )

        assert response.status_code == 200

    def test_submit_promotion_config_accepts_empty_payload(
        self,
        client,
        admin_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/promotion-config",
            headers=admin_headers,
            json={},
        )

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "payload",
        [
            {
                "rules": [
                    {
                        "name": "",
                        "from_level_name": "Primary 1",
                    }
                ]
            },
            {
                "rules": [
                    {
                        "name": "Primary Promotion",
                        "from_level_name": "",
                    }
                ]
            },
        ],
    )
    def test_submit_promotion_config_rejects_invalid_payload(
        self,
        client,
        admin_headers,
        school,
        payload,
    ):
        response = client.post(
            f"/onboarding/{school.id}/promotion-config",
            headers=admin_headers,
            json=payload,
        )

        assert response.status_code in (400, 422)

    def test_submit_promotion_config_rejects_unknown_from_level(
        self,
        client,
        admin_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/promotion-config",
            headers=admin_headers,
            json={
                "rules": [
                    {
                        "name": "Unknown Level Promotion",
                        "from_level_name": "Does Not Exist",
                        "to_level_name": None,
                    }
                ]
            },
        )

        assert response.status_code == 400

    def test_submit_promotion_config_rejects_unknown_to_level(
        self,
        client,
        admin_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/academic-structure",
            headers=admin_headers,
            json=academic_structure_payload(),
        )

        assert response.status_code == 200

        response = client.post(
            f"/onboarding/{school.id}/promotion-config",
            headers=admin_headers,
            json={
                "rules": [
                    {
                        "name": "Invalid Target Promotion",
                        "from_level_name": "Primary 1",
                        "to_level_name": "Does Not Exist",
                    }
                ]
            },
        )

        assert response.status_code == 400

    def test_submit_promotion_config_rejects_teacher(
        self,
        client,
        teacher_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/promotion-config",
            headers=teacher_headers,
            json=promotion_config_payload(),
        )

        assert response.status_code == 403

    def test_submit_promotion_config_requires_authentication(
        self,
        client,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/promotion-config",
            json=promotion_config_payload(),
        )

        assert response.status_code == 401


# ============================================================================
# ADMIN ACCOUNT
# ============================================================================

class TestSubmitAdminAccountRoute:

    def test_submit_admin_account_success(
        self,
        client,
        admin_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/admin-account",
            headers=admin_headers,
            json={
                "username": "schooladmin",
                "email": "admin@testschool.com",
                "password": "StrongPassword123!",
            },
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["school_id"] == school.id
        assert "admin_account" in data["completed_steps"]

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {
                "email": "admin@testschool.com",
                "password": "StrongPassword123!",
            },
            {
                "username": "ab",
                "email": "admin@testschool.com",
                "password": "StrongPassword123!",
            },
            {
                "username": "schooladmin",
                "email": "x" * 256,
                "password": "StrongPassword123!",
            },
            {
                "username": "schooladmin",
                "email": "admin@testschool.com",
                "password": "123",
            },
        ],
    )
    def test_submit_admin_account_rejects_invalid_payload(
        self,
        client,
        admin_headers,
        school,
        payload,
    ):
        response = client.post(
            f"/onboarding/{school.id}/admin-account",
            headers=admin_headers,
            json=payload,
        )

        assert response.status_code in (400, 422)

    def test_submit_admin_account_rejects_teacher(
        self,
        client,
        teacher_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/admin-account",
            headers=teacher_headers,
            json={
                "username": "schooladmin",
                "email": "admin@testschool.com",
                "password": "StrongPassword123!",
            },
        )

        assert response.status_code == 403

    def test_submit_admin_account_requires_authentication(
        self,
        client,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/admin-account",
            json={
                "username": "schooladmin",
                "email": "admin@testschool.com",
                "password": "StrongPassword123!",
            },
        )

        assert response.status_code == 401


# ============================================================================
# COMPLETE ONBOARDING
# ============================================================================

class TestCompleteOnboardingRoute:

    def _complete_all_required_steps(
        self,
        client,
        admin_headers,
        school,
    ):
        # Step 1: school info
        response = client.post(
            f"/onboarding/{school.id}/school-info",
            headers=admin_headers,
            json={
                "name": "Completed Test School",
                "slug": "completed-test-school",
                "country": "Nigeria",
            },
        )
        assert response.status_code == 200

        # Step 2: localization
        response = client.post(
            f"/onboarding/{school.id}/localization",
            headers=admin_headers,
            json={
                "timezone": "Africa/Lagos",
                "currency": "NGN",
                "locale": "en-NG",
            },
        )
        assert response.status_code == 200

        # Step 3: academic structure
        response = client.post(
            f"/onboarding/{school.id}/academic-structure",
            headers=admin_headers,
            json=academic_structure_payload(),
        )
        assert response.status_code == 200

        # Step 4: grading config
        response = client.post(
            f"/onboarding/{school.id}/grading-config",
            headers=admin_headers,
            json=grading_config_payload(),
        )
        assert response.status_code == 200, response.get_json()

        # Step 5: promotion config
        response = client.post(
            f"/onboarding/{school.id}/promotion-config",
            headers=admin_headers,
            json=promotion_config_payload(),
        )
        assert response.status_code == 200

        # Step 6: admin account
        response = client.post(
            f"/onboarding/{school.id}/admin-account",
            headers=admin_headers,
            json={
                "username": "onboardedadmin",
                "email": "onboardedadmin@testschool.com",
                "password": "StrongPassword123!",
            },
        )
        assert response.status_code == 200

    def test_complete_onboarding_success(
        self,
        client,
        admin_headers,
        school,
    ):
        self._complete_all_required_steps(
            client,
            admin_headers,
            school,
        )

        response = client.post(
            f"/onboarding/{school.id}/complete",
            headers=admin_headers,
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["school_id"] == school.id
        assert data["is_completed"] is True
        assert data["current_step"] == OnboardingStep.DONE.value
        assert data["completed_at"] is not None

        assert set(data["completed_steps"]) >= {
            OnboardingStep.SCHOOL_INFO.value,
            OnboardingStep.LOCALIZATION.value,
            OnboardingStep.ACADEMIC_STRUCTURE.value,
            OnboardingStep.GRADING_CONFIG.value,
            OnboardingStep.PROMOTION_CONFIG.value,
            OnboardingStep.ADMIN_ACCOUNT.value,
            OnboardingStep.REVIEW.value,
           }

    def test_complete_onboarding_rejects_when_not_started(
        self,
        client,
        admin_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/complete",
            headers=admin_headers,
        )

        assert response.status_code == 400

    def test_complete_onboarding_rejects_teacher(
        self,
        client,
        teacher_headers,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/complete",
            headers=teacher_headers,
        )

        assert response.status_code == 403

    def test_complete_onboarding_requires_authentication(
        self,
        client,
        school,
    ):
        response = client.post(
            f"/onboarding/{school.id}/complete",
        )
        assert response.status_code == 401