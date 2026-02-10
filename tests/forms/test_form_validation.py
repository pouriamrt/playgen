"""Form field validation tests.

Tests for client-side and server-side field validation including required fields,
format validation, boundary checks, and error message presentation.
"""
from __future__ import annotations

import pytest
from faker import Faker
from playwright.sync_api import Page, expect

from pages.form_page import FormPage

fake = Faker()

pytestmark = [pytest.mark.forms, pytest.mark.regression]


# ---------------------------------------------------------------------------
# Required field validation
# ---------------------------------------------------------------------------


class TestRequiredFieldValidation:
    """Tests that required fields display appropriate error messages."""

    def test_required_fields_show_error_when_empty(
        self, navigate_to_form: FormPage
    ) -> None:
        """Submitting a form with all required fields empty should show errors."""
        form = navigate_to_form

        # Act
        form.submit()

        # Assert
        for field in ("first_name", "last_name", "email"):
            assert form.is_validation_error_visible(field), (
                f"Expected validation error for required field '{field}'"
            )

    @pytest.mark.parametrize(
        "field",
        ["first_name", "last_name", "email"],
        ids=["first_name", "last_name", "email"],
    )
    def test_individual_required_field_shows_error(
        self, navigate_to_form: FormPage, field: str
    ) -> None:
        """Each required field should independently show an error when left blank."""
        form = navigate_to_form

        # Act - fill all except the target field, then submit
        all_fields = {"first_name": fake.first_name(), "last_name": fake.last_name(), "email": fake.email()}
        for name, value in all_fields.items():
            if name != field:
                form.fill_field(name, value)
        form.submit()

        # Assert
        assert form.is_validation_error_visible(field)

    def test_select_field_requires_selection(
        self, navigate_to_form: FormPage
    ) -> None:
        """A required dropdown select should show an error when no option is selected."""
        form = navigate_to_form

        # Act
        form.submit()

        # Assert
        assert form.is_validation_error_visible("category")

    def test_checkbox_required_validation(
        self, navigate_to_form: FormPage
    ) -> None:
        """A required checkbox (e.g. terms agreement) should produce an error when unchecked."""
        form = navigate_to_form

        # Act
        form.submit()

        # Assert
        assert form.is_validation_error_visible("terms")


# ---------------------------------------------------------------------------
# Email validation
# ---------------------------------------------------------------------------


class TestEmailValidation:
    """Tests for email field format validation."""

    @pytest.mark.parametrize(
        "invalid_email",
        [
            "plainaddress",
            "@missing-local.com",
            "missing-at-sign.com",
            "missing@.com",
            "missing@domain",
            "spaces in@email.com",
            "double@@at.com",
            "",
        ],
        ids=[
            "no_at_or_domain",
            "missing_local_part",
            "no_at_sign",
            "missing_domain_name",
            "missing_tld",
            "spaces_in_local",
            "double_at",
            "empty_string",
        ],
    )
    def test_email_field_rejects_invalid_format(
        self, navigate_to_form: FormPage, invalid_email: str
    ) -> None:
        """Email field should reject obviously invalid email formats."""
        form = navigate_to_form

        # Act
        form.fill_field("email", invalid_email)
        form.submit()

        # Assert
        assert form.is_validation_error_visible("email")

    @pytest.mark.parametrize(
        "valid_email",
        [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.com",
            "user@sub.domain.com",
        ],
        ids=["simple", "dotted_local", "plus_tag", "subdomain"],
    )
    def test_email_field_accepts_valid_format(
        self, navigate_to_form: FormPage, valid_email: str
    ) -> None:
        """Email field should accept well-formed email addresses."""
        form = navigate_to_form

        # Act
        form.fill_field("email", valid_email)
        form.page.locator(form.INPUT_TEMPLATE.format(name="email")).blur()

        # Assert
        assert not form.is_validation_error_visible("email")


# ---------------------------------------------------------------------------
# Phone validation
# ---------------------------------------------------------------------------


class TestPhoneValidation:
    """Tests for phone number field validation."""

    @pytest.mark.parametrize(
        "valid_phone",
        [
            "555-123-4567",
            "(555) 123-4567",
            "+1 555 123 4567",
            "5551234567",
        ],
        ids=["dashes", "parens_and_dashes", "international", "digits_only"],
    )
    def test_phone_field_accepts_valid_numbers(
        self, navigate_to_form: FormPage, valid_phone: str
    ) -> None:
        """Phone field should accept common phone number formats."""
        form = navigate_to_form

        # Act
        form.fill_field("phone", valid_phone)
        form.page.locator(form.INPUT_TEMPLATE.format(name="phone")).blur()

        # Assert
        assert not form.is_validation_error_visible("phone")

    @pytest.mark.parametrize(
        "invalid_phone",
        [
            "abc-def-ghij",
            "12",
            "++1-555",
        ],
        ids=["letters", "too_short", "double_plus"],
    )
    def test_phone_field_rejects_invalid_numbers(
        self, navigate_to_form: FormPage, invalid_phone: str
    ) -> None:
        """Phone field should reject invalid phone number strings."""
        form = navigate_to_form

        # Act
        form.fill_field("phone", invalid_phone)
        form.submit()

        # Assert
        assert form.is_validation_error_visible("phone")


# ---------------------------------------------------------------------------
# Text field length validation
# ---------------------------------------------------------------------------


class TestTextLengthValidation:
    """Tests for minimum and maximum length constraints on text fields."""

    def test_text_field_min_length_validation(
        self, navigate_to_form: FormPage
    ) -> None:
        """A text field with a minimum length should reject input that is too short."""
        form = navigate_to_form

        # Act
        form.fill_field("first_name", "A")
        form.submit()

        # Assert
        assert form.is_validation_error_visible("first_name")

    def test_text_field_max_length_validation(
        self, navigate_to_form: FormPage
    ) -> None:
        """A text field with a maximum length should reject input that is too long."""
        form = navigate_to_form

        # Act
        form.fill_field("first_name", "A" * 256)
        form.submit()

        # Assert
        assert form.is_validation_error_visible("first_name")

    def test_textarea_max_length(
        self, navigate_to_form: FormPage
    ) -> None:
        """A textarea field should enforce its maximum character limit."""
        form = navigate_to_form

        # Act
        form.fill_textarea("description", "x" * 5001)
        form.submit()

        # Assert
        assert form.is_validation_error_visible("description")


# ---------------------------------------------------------------------------
# Number field validation
# ---------------------------------------------------------------------------


class TestNumberFieldValidation:
    """Tests for numeric input field boundaries."""

    def test_number_field_min_value(
        self, navigate_to_form: FormPage
    ) -> None:
        """Number field should reject values below the minimum."""
        form = navigate_to_form

        # Act
        form.fill_field("age", "-1")
        form.submit()

        # Assert
        assert form.is_validation_error_visible("age")

    def test_number_field_max_value(
        self, navigate_to_form: FormPage
    ) -> None:
        """Number field should reject values above the maximum."""
        form = navigate_to_form

        # Act
        form.fill_field("age", "200")
        form.submit()

        # Assert
        assert form.is_validation_error_visible("age")

    def test_number_field_rejects_non_numeric(
        self, navigate_to_form: FormPage
    ) -> None:
        """Number field should reject non-numeric input."""
        form = navigate_to_form

        # Act
        form.fill_field("age", "not-a-number")
        form.submit()

        # Assert
        assert form.is_validation_error_visible("age")


# ---------------------------------------------------------------------------
# URL field validation
# ---------------------------------------------------------------------------


class TestURLFieldValidation:
    """Tests for URL format validation."""

    @pytest.mark.parametrize(
        "invalid_url",
        [
            "not a url",
            "ftp:/missing-slash.com",
            "://no-scheme.com",
            "http://",
        ],
        ids=["plain_text", "malformed_scheme", "no_scheme", "empty_host"],
    )
    def test_url_field_validation(
        self, navigate_to_form: FormPage, invalid_url: str
    ) -> None:
        """URL field should reject malformed URLs."""
        form = navigate_to_form

        # Act
        form.fill_field("website", invalid_url)
        form.submit()

        # Assert
        assert form.is_validation_error_visible("website")


# ---------------------------------------------------------------------------
# Date field validation
# ---------------------------------------------------------------------------


class TestDateFieldValidation:
    """Tests for date input validation."""

    def test_date_field_validation(
        self, navigate_to_form: FormPage
    ) -> None:
        """Date field should reject invalid date strings."""
        form = navigate_to_form

        # Act
        form.set_date("start_date", "not-a-date")
        form.submit()

        # Assert
        assert form.is_validation_error_visible("start_date")

    def test_date_range_validation(
        self, navigate_to_form: FormPage
    ) -> None:
        """Start date must be before end date."""
        form = navigate_to_form

        # Act - set end date before start date
        form.set_date("start_date", "2025-12-31")
        form.set_date("end_date", "2025-01-01")
        form.submit()

        # Assert
        assert form.is_validation_error_visible("end_date")


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------


class TestPasswordValidation:
    """Tests for password strength and confirmation validation."""

    @pytest.mark.parametrize(
        "weak_password",
        [
            "short",
            "alllowercase",
            "ALLUPPERCASE",
            "NoDigitsHere!",
            "12345678",
        ],
        ids=["too_short", "no_uppercase", "no_lowercase", "no_digits", "digits_only"],
    )
    def test_password_field_strength_validation(
        self, navigate_to_form: FormPage, weak_password: str
    ) -> None:
        """Password field should enforce strength requirements."""
        form = navigate_to_form

        # Act
        form.fill_field("password", weak_password)
        form.submit()

        # Assert
        assert form.is_validation_error_visible("password")

    def test_confirm_field_must_match(
        self, navigate_to_form: FormPage
    ) -> None:
        """Password confirmation field must match the password field."""
        form = navigate_to_form

        # Act
        form.fill_field("password", "StrongP@ss1")
        form.fill_field("confirm_password", "DifferentP@ss2")
        form.submit()

        # Assert
        assert form.is_validation_error_visible("confirm_password")


# ---------------------------------------------------------------------------
# Special character and encoding tests
# ---------------------------------------------------------------------------


class TestSpecialCharacterHandling:
    """Tests for special characters, Unicode, and HTML in form fields."""

    def test_special_characters_in_text_fields(
        self, navigate_to_form: FormPage
    ) -> None:
        """Text fields should accept special characters without errors."""
        form = navigate_to_form

        # Act
        form.fill_field("first_name", "O'Brien-Smith")
        form.fill_field("last_name", "De la Cruz")
        form.fill_field("email", "user@example.com")
        form.submit()

        # Assert - no validation error for names with apostrophes/hyphens
        assert not form.is_validation_error_visible("first_name")
        assert not form.is_validation_error_visible("last_name")

    def test_unicode_characters_in_text_fields(
        self, navigate_to_form: FormPage
    ) -> None:
        """Text fields should handle Unicode characters correctly."""
        form = navigate_to_form

        # Act
        form.fill_field("first_name", "\u00e9\u00e8\u00ea\u00eb")
        form.fill_field("last_name", "\u00fc\u00f1\u00ed\u00e7\u00f6\u00f0\u00e9")
        form.fill_field("email", "user@example.com")
        form.submit()

        # Assert
        assert not form.is_validation_error_visible("first_name")
        assert not form.is_validation_error_visible("last_name")

    def test_html_tags_stripped_or_escaped(
        self, navigate_to_form: FormPage
    ) -> None:
        """HTML tags in text fields should be stripped or escaped on submission."""
        form = navigate_to_form

        # Act
        form.fill_field("first_name", "<script>alert('xss')</script>")
        form.fill_field("last_name", "Normal")
        form.fill_field("email", "user@example.com")
        form.submit()

        # Assert - the raw script tag should not appear in the field value
        value = form.get_field_value("first_name")
        assert "<script>" not in value

    def test_leading_trailing_whitespace_trimmed(
        self, navigate_to_form: FormPage
    ) -> None:
        """Leading and trailing whitespace in text fields should be trimmed."""
        form = navigate_to_form

        # Act
        form.fill_field("email", "  user@example.com  ")
        form.submit()

        # Assert
        value = form.get_field_value("email")
        assert value == value.strip()


# ---------------------------------------------------------------------------
# Validation message UX
# ---------------------------------------------------------------------------


class TestValidationMessageUX:
    """Tests that validation messages behave correctly from a UX perspective."""

    def test_validation_messages_are_descriptive(
        self, navigate_to_form: FormPage
    ) -> None:
        """Validation error messages should be descriptive, not blank."""
        form = navigate_to_form

        # Act
        form.submit()

        # Assert
        error_text = form.get_validation_error("email")
        assert len(error_text) > 0, "Validation message should not be empty"

    def test_validation_messages_clear_on_correction(
        self, navigate_to_form: FormPage
    ) -> None:
        """Validation errors should disappear once the field is corrected."""
        form = navigate_to_form

        # Arrange - trigger an error
        form.submit()
        assert form.is_validation_error_visible("email")

        # Act - correct the field
        form.fill_field("email", fake.email())
        form.page.locator(form.INPUT_TEMPLATE.format(name="email")).blur()

        # Assert
        assert not form.is_validation_error_visible("email")

    def test_inline_validation_on_blur(
        self, navigate_to_form: FormPage
    ) -> None:
        """Fields should show inline validation when the user tabs away (blur)."""
        form = navigate_to_form

        # Act
        form.fill_field("email", "invalid")
        form.page.locator(form.INPUT_TEMPLATE.format(name="email")).blur()

        # Assert
        assert form.is_validation_error_visible("email")

    def test_form_level_validation_on_submit(
        self, navigate_to_form: FormPage
    ) -> None:
        """Form-level validation summary should appear on submit with multiple errors."""
        form = navigate_to_form

        # Act
        form.submit()

        # Assert - a general form-level error summary should be visible
        assert form.is_visible('[data-testid="form-error-summary"]')
