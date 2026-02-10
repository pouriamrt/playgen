"""Form submission tests.

Tests for form submission flows including success, error handling,
multi-step forms, dirty state detection, and network resilience.
"""
from __future__ import annotations

import pytest
from faker import Faker
from playwright.sync_api import Page, Route, expect

from pages.form_page import FormPage
from pages.modal_page import ModalPage
from utils.api_client import APIClient

fake = Faker()

pytestmark = [pytest.mark.forms, pytest.mark.regression]


# ---------------------------------------------------------------------------
# Successful submission
# ---------------------------------------------------------------------------


class TestSuccessfulSubmission:
    """Tests for the happy-path form submission flow."""

    @pytest.mark.smoke
    def test_successful_form_submission(
        self, navigate_to_form: FormPage, sample_form_data: dict[str, str]
    ) -> None:
        """A fully valid form should submit successfully without errors."""
        form = navigate_to_form

        # Act
        form.fill_field("first_name", sample_form_data["first_name"])
        form.fill_field("last_name", sample_form_data["last_name"])
        form.fill_field("email", sample_form_data["email"])
        form.fill_field("phone", sample_form_data["phone"])
        form.submit()

        # Assert - no validation errors should be visible
        assert not form.is_validation_error_visible("first_name")
        assert not form.is_validation_error_visible("email")

    @pytest.mark.smoke
    def test_form_submission_shows_success_message(
        self, navigate_to_form: FormPage, sample_form_data: dict[str, str]
    ) -> None:
        """After successful submission, a success notification should appear."""
        form = navigate_to_form

        # Act
        form.fill_field("first_name", sample_form_data["first_name"])
        form.fill_field("last_name", sample_form_data["last_name"])
        form.fill_field("email", sample_form_data["email"])
        form.submit()

        # Assert
        assert form.is_visible('[data-testid="success-message"]')

    def test_form_submission_redirects_correctly(
        self, navigate_to_form: FormPage, sample_form_data: dict[str, str]
    ) -> None:
        """After successful submission, the user should be redirected."""
        form = navigate_to_form

        # Act
        form.fill_field("first_name", sample_form_data["first_name"])
        form.fill_field("last_name", sample_form_data["last_name"])
        form.fill_field("email", sample_form_data["email"])
        form.submit()

        # Assert
        form.wait_for_navigation("**/forms/**")
        assert "/forms/" in form.get_current_url()

    def test_form_data_persisted_to_backend(
        self,
        navigate_to_form: FormPage,
        sample_form_data: dict[str, str],
        api_client: APIClient,
    ) -> None:
        """Submitted form data should be persisted and retrievable via the API."""
        form = navigate_to_form

        # Act
        form.fill_field("first_name", sample_form_data["first_name"])
        form.fill_field("last_name", sample_form_data["last_name"])
        form.fill_field("email", sample_form_data["email"])
        form.submit()
        form.wait_for_navigation("**/forms/**")

        # Assert - verify via API
        response = api_client.get("/forms", params={"email": sample_form_data["email"]})
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0
        assert data["results"][0]["email"] == sample_form_data["email"]

    def test_form_submission_with_all_field_types(
        self, navigate_to_form: FormPage, sample_form_data: dict[str, str]
    ) -> None:
        """A form using every supported field type should submit correctly."""
        form = navigate_to_form

        # Act - fill every field type
        form.fill_field("first_name", sample_form_data["first_name"])
        form.fill_field("last_name", sample_form_data["last_name"])
        form.fill_field("email", sample_form_data["email"])
        form.fill_field("phone", sample_form_data["phone"])
        form.fill_field("website", sample_form_data["website"])
        form.fill_textarea("description", sample_form_data["description"])
        form.select_dropdown("category", "general")
        form.check_checkbox("terms")
        form.select_radio("priority", "medium")
        form.set_date("start_date", "2025-06-01")
        form.submit()

        # Assert
        assert form.is_visible('[data-testid="success-message"]')


# ---------------------------------------------------------------------------
# Submit button behaviour
# ---------------------------------------------------------------------------


class TestSubmitButtonBehaviour:
    """Tests for submit button state during and after submission."""

    def test_form_submit_button_disabled_during_submission(
        self, navigate_to_form: FormPage, sample_form_data: dict[str, str]
    ) -> None:
        """The submit button should be disabled while the form is submitting."""
        form = navigate_to_form

        # Arrange
        form.fill_field("first_name", sample_form_data["first_name"])
        form.fill_field("last_name", sample_form_data["last_name"])
        form.fill_field("email", sample_form_data["email"])

        # Intercept API to slow down submission
        form.page.route(
            "**/api/forms**",
            lambda route: route.fulfill(status=200, body='{"id":1}', headers={"Content-Type": "application/json"}),
        )

        # Act
        form.click(form.SUBMIT_BUTTON)

        # Assert
        expect(form.page.locator(form.SUBMIT_BUTTON)).to_be_disabled()

    def test_form_prevents_double_submission(
        self, navigate_to_form: FormPage, sample_form_data: dict[str, str]
    ) -> None:
        """Clicking submit twice rapidly should not produce duplicate submissions."""
        form = navigate_to_form
        submission_count = {"value": 0}

        def count_submissions(route: Route) -> None:
            submission_count["value"] += 1
            route.fulfill(status=200, body='{"id":1}', headers={"Content-Type": "application/json"})

        form.page.route("**/api/forms**", count_submissions)

        # Arrange
        form.fill_field("first_name", sample_form_data["first_name"])
        form.fill_field("last_name", sample_form_data["last_name"])
        form.fill_field("email", sample_form_data["email"])

        # Act - double-click submit
        form.click(form.SUBMIT_BUTTON)
        form.click(form.SUBMIT_BUTTON)

        # Assert
        form.page.wait_for_timeout(1000)
        assert submission_count["value"] == 1, "Form should prevent double submission"

    def test_form_submit_with_enter_key(
        self, navigate_to_form: FormPage, sample_form_data: dict[str, str]
    ) -> None:
        """Pressing Enter in a text field should trigger form submission."""
        form = navigate_to_form

        # Arrange
        form.fill_field("first_name", sample_form_data["first_name"])
        form.fill_field("last_name", sample_form_data["last_name"])
        form.fill_field("email", sample_form_data["email"])

        # Act - press Enter in the last field
        form.page.locator(form.INPUT_TEMPLATE.format(name="email")).press("Enter")

        # Assert
        form.page.wait_for_timeout(500)
        assert form.is_visible('[data-testid="success-message"]') or "/forms/" in form.get_current_url()


# ---------------------------------------------------------------------------
# Cancel and reset
# ---------------------------------------------------------------------------


class TestCancelAndReset:
    """Tests for form cancel and reset actions."""

    def test_form_cancel_discards_changes(
        self, navigate_to_form: FormPage, sample_form_data: dict[str, str]
    ) -> None:
        """Clicking cancel should discard entered data and navigate away."""
        form = navigate_to_form

        # Arrange
        form.fill_field("first_name", sample_form_data["first_name"])

        # Act
        form.cancel()

        # Assert - should navigate away from form
        form.page.wait_for_timeout(500)
        assert "/forms/create" not in form.get_current_url()

    def test_form_reset_clears_all_fields(
        self, navigate_to_form: FormPage, sample_form_data: dict[str, str]
    ) -> None:
        """Clicking the reset button should clear all form fields."""
        form = navigate_to_form

        # Arrange
        form.fill_field("first_name", sample_form_data["first_name"])
        form.fill_field("email", sample_form_data["email"])

        # Act
        form.click('[data-testid="form-reset"]')

        # Assert
        assert form.get_field_value("first_name") == ""
        assert form.get_field_value("email") == ""

    def test_form_dirty_state_detection(
        self, navigate_to_form: FormPage, modal_page: ModalPage
    ) -> None:
        """Navigating away from a dirty form should prompt an unsaved changes warning."""
        form = navigate_to_form

        # Arrange - make the form dirty
        form.fill_field("first_name", "Unsaved Data")

        # Act - try to navigate away
        form.page.locator('[data-testid="nav-home"]').click()

        # Assert - unsaved changes modal should appear
        modal_page.wait_for_open()
        assert "unsaved" in modal_page.get_body_text().lower()


# ---------------------------------------------------------------------------
# Error handling and resilience
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for form behaviour when submission encounters errors."""

    def test_form_submit_with_network_error(
        self, navigate_to_form: FormPage, sample_form_data: dict[str, str]
    ) -> None:
        """A network error during submission should show an error message."""
        form = navigate_to_form

        # Arrange - simulate network failure
        form.page.route("**/api/forms**", lambda route: route.abort("connectionrefused"))
        form.fill_field("first_name", sample_form_data["first_name"])
        form.fill_field("last_name", sample_form_data["last_name"])
        form.fill_field("email", sample_form_data["email"])

        # Act
        form.submit()

        # Assert
        form.page.wait_for_timeout(1000)
        assert form.is_visible('[data-testid="error-message"]')

    def test_form_retry_after_error(
        self, navigate_to_form: FormPage, sample_form_data: dict[str, str]
    ) -> None:
        """After a submission error, the user should be able to retry."""
        form = navigate_to_form
        call_count = {"value": 0}

        def fail_then_succeed(route: Route) -> None:
            call_count["value"] += 1
            if call_count["value"] == 1:
                route.abort("connectionrefused")
            else:
                route.fulfill(status=200, body='{"id":1}', headers={"Content-Type": "application/json"})

        form.page.route("**/api/forms**", fail_then_succeed)

        # Arrange
        form.fill_field("first_name", sample_form_data["first_name"])
        form.fill_field("last_name", sample_form_data["last_name"])
        form.fill_field("email", sample_form_data["email"])

        # Act - first submit fails
        form.submit()
        form.page.wait_for_timeout(1000)

        # Act - retry
        form.submit()
        form.page.wait_for_timeout(1000)

        # Assert
        assert form.is_visible('[data-testid="success-message"]')

    def test_form_preserves_data_on_validation_error(
        self, navigate_to_form: FormPage, sample_form_data: dict[str, str]
    ) -> None:
        """When submission fails validation, entered data should be preserved."""
        form = navigate_to_form

        # Arrange - fill some fields but leave required email blank
        form.fill_field("first_name", sample_form_data["first_name"])
        form.fill_field("last_name", sample_form_data["last_name"])

        # Act
        form.submit()

        # Assert - data should still be present
        assert form.get_field_value("first_name") == sample_form_data["first_name"]
        assert form.get_field_value("last_name") == sample_form_data["last_name"]


# ---------------------------------------------------------------------------
# Multi-step / wizard forms
# ---------------------------------------------------------------------------


class TestMultiStepForm:
    """Tests for multi-step (wizard) form navigation and data persistence."""

    NEXT_BUTTON = '[data-testid="form-next"]'
    BACK_BUTTON = '[data-testid="form-back"]'
    STEP_INDICATOR = '[data-testid="step-indicator"]'

    def _navigate_to_wizard(self, form: FormPage) -> None:
        """Helper to navigate to the multi-step form."""
        form.navigate("/forms/wizard")
        form.wait_for_load()

    def test_multi_step_form_navigation(
        self, form_page: FormPage
    ) -> None:
        """User should be able to navigate forward through wizard steps."""
        form = form_page
        self._navigate_to_wizard(form)

        # Act - fill step 1 and go to step 2
        form.fill_field("first_name", fake.first_name())
        form.fill_field("last_name", fake.last_name())
        form.click(self.NEXT_BUTTON)

        # Assert
        assert form.is_visible('[data-testid="step-2"]')

    def test_multi_step_form_data_persistence(
        self, form_page: FormPage
    ) -> None:
        """Data entered in earlier steps should persist when moving forward."""
        form = form_page
        self._navigate_to_wizard(form)
        first_name = fake.first_name()

        # Act - fill step 1, go to step 2, then go back
        form.fill_field("first_name", first_name)
        form.fill_field("last_name", fake.last_name())
        form.click(self.NEXT_BUTTON)
        form.page.wait_for_timeout(300)
        form.click(self.BACK_BUTTON)
        form.page.wait_for_timeout(300)

        # Assert
        assert form.get_field_value("first_name") == first_name

    def test_multi_step_form_back_preserves_data(
        self, form_page: FormPage
    ) -> None:
        """Going back from step 2 should preserve step 2 data when returning."""
        form = form_page
        self._navigate_to_wizard(form)
        email = fake.email()

        # Arrange - complete step 1
        form.fill_field("first_name", fake.first_name())
        form.fill_field("last_name", fake.last_name())
        form.click(self.NEXT_BUTTON)
        form.page.wait_for_timeout(300)

        # Act - fill step 2, go back, then return to step 2
        form.fill_field("email", email)
        form.click(self.BACK_BUTTON)
        form.page.wait_for_timeout(300)
        form.click(self.NEXT_BUTTON)
        form.page.wait_for_timeout(300)

        # Assert
        assert form.get_field_value("email") == email

    def test_multi_step_form_progress_indicator(
        self, form_page: FormPage
    ) -> None:
        """The progress indicator should reflect the current step."""
        form = form_page
        self._navigate_to_wizard(form)

        # Assert step 1 is active
        step_indicator = form.page.locator(self.STEP_INDICATOR)
        expect(step_indicator).to_contain_text("1")

        # Act - move to step 2
        form.fill_field("first_name", fake.first_name())
        form.fill_field("last_name", fake.last_name())
        form.click(self.NEXT_BUTTON)
        form.page.wait_for_timeout(300)

        # Assert step 2 is active
        expect(step_indicator).to_contain_text("2")


# ---------------------------------------------------------------------------
# Conditional and dynamic fields
# ---------------------------------------------------------------------------


class TestConditionalFields:
    """Tests for conditional fields that show/hide based on user selections."""

    def test_conditional_form_fields(
        self, navigate_to_form: FormPage
    ) -> None:
        """Selecting a category should reveal additional fields."""
        form = navigate_to_form

        # Assert - additional fields hidden initially
        assert not form.is_visible('[data-testid="field-company"]')

        # Act - select 'business' category
        form.select_dropdown("category", "business")

        # Assert - company field should now be visible
        form.page.wait_for_timeout(300)
        assert form.is_visible('[data-testid="field-company"]')

    def test_dynamic_form_field_addition(
        self, navigate_to_form: FormPage
    ) -> None:
        """Clicking 'Add another' should dynamically add a new field group."""
        form = navigate_to_form

        # Arrange - count initial fields
        initial_count = form.get_element_count('[data-testid^="dynamic-field-"]')

        # Act
        form.click('[data-testid="add-field-button"]')
        form.page.wait_for_timeout(300)

        # Assert
        new_count = form.get_element_count('[data-testid^="dynamic-field-"]')
        assert new_count == initial_count + 1


# ---------------------------------------------------------------------------
# Autosave
# ---------------------------------------------------------------------------


class TestFormAutosave:
    """Tests for form autosave / draft functionality."""

    def test_form_autosave_draft(
        self, form_page: FormPage
    ) -> None:
        """Form should autosave a draft after the user types and pauses."""
        form = form_page
        form.navigate("/forms/create")
        form.wait_for_load()
        saved_requests: list[dict] = []

        def capture_save(route: Route) -> None:
            saved_requests.append({"url": route.request.url})
            route.fulfill(status=200, body='{"draft_id":1}', headers={"Content-Type": "application/json"})

        form.page.route("**/api/forms/draft**", capture_save)

        # Act - type some data and wait for autosave
        form.fill_field("first_name", fake.first_name())
        form.page.wait_for_timeout(3000)  # typical autosave delay

        # Assert
        assert len(saved_requests) > 0, "Autosave request should have been sent"
