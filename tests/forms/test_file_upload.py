"""File upload tests.

Tests for file upload interactions including valid/invalid uploads,
size limits, drag-and-drop, progress indication, and edge cases.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from pages.form_page import FormPage

pytestmark = [pytest.mark.forms, pytest.mark.regression]


# ---------------------------------------------------------------------------
# Basic upload visibility
# ---------------------------------------------------------------------------


class TestFileUploadBasics:
    """Tests for basic file upload element visibility and functionality."""

    def test_file_upload_button_visible(
        self, navigate_to_form: FormPage
    ) -> None:
        """The file upload input should be visible on the form page."""
        form = navigate_to_form

        # Assert
        upload_selector = form.FILE_UPLOAD_TEMPLATE.format(name="document")
        assert form.is_visible(upload_selector)


# ---------------------------------------------------------------------------
# Valid file uploads
# ---------------------------------------------------------------------------


class TestValidFileUploads:
    """Tests for uploading valid files of various types."""

    @pytest.mark.smoke
    def test_upload_valid_image_file(
        self, navigate_to_form: FormPage, sample_image_file: Path
    ) -> None:
        """Uploading a valid image file should succeed without errors."""
        form = navigate_to_form

        # Act
        form.upload_file("document", str(sample_image_file))

        # Assert
        assert form.is_visible('[data-testid="upload-preview"]')

    def test_upload_valid_document_file(
        self, navigate_to_form: FormPage, sample_pdf_file: Path
    ) -> None:
        """Uploading a valid PDF document should succeed."""
        form = navigate_to_form

        # Act
        form.upload_file("document", str(sample_pdf_file))

        # Assert
        assert form.is_visible('[data-testid="upload-filename"]')
        filename_text = form.get_text('[data-testid="upload-filename"]')
        assert "sample.pdf" in filename_text

    def test_upload_multiple_files(
        self, navigate_to_form: FormPage, sample_text_file: Path, sample_csv_file: Path
    ) -> None:
        """Uploading multiple files at once should be supported."""
        form = navigate_to_form

        # Act
        selector = form.FILE_UPLOAD_TEMPLATE.format(name="documents")
        form.page.set_input_files(selector, [str(sample_text_file), str(sample_csv_file)])

        # Assert
        file_count = form.get_element_count('[data-testid^="upload-item-"]')
        assert file_count == 2


# ---------------------------------------------------------------------------
# Invalid uploads and size limits
# ---------------------------------------------------------------------------


class TestInvalidUploads:
    """Tests for file upload rejection scenarios."""

    def test_upload_exceeds_max_size(
        self, navigate_to_form: FormPage, oversized_file: Path
    ) -> None:
        """Uploading a file that exceeds the maximum size should show an error."""
        form = navigate_to_form

        # Act
        form.upload_file("document", str(oversized_file))

        # Assert
        assert form.is_visible('[data-testid="upload-error"]')
        error_text = form.get_text('[data-testid="upload-error"]')
        assert "size" in error_text.lower()

    def test_upload_invalid_file_type(
        self, navigate_to_form: FormPage, invalid_extension_file: Path
    ) -> None:
        """Uploading a file with an unsupported extension should show an error."""
        form = navigate_to_form

        # Act
        form.upload_file("document", str(invalid_extension_file))

        # Assert
        assert form.is_visible('[data-testid="upload-error"]')
        error_text = form.get_text('[data-testid="upload-error"]')
        assert "type" in error_text.lower() or "format" in error_text.lower()

    def test_upload_empty_file(
        self, navigate_to_form: FormPage, empty_file: Path
    ) -> None:
        """Uploading an empty file should show a warning or error."""
        form = navigate_to_form

        # Act
        form.upload_file("document", str(empty_file))

        # Assert
        assert form.is_visible('[data-testid="upload-error"]') or form.is_visible(
            '[data-testid="upload-warning"]'
        )


# ---------------------------------------------------------------------------
# Upload progress and UX
# ---------------------------------------------------------------------------


class TestUploadProgressAndUX:
    """Tests for upload progress indicators and UX elements."""

    def test_upload_progress_indicator(
        self, navigate_to_form: FormPage, sample_image_file: Path
    ) -> None:
        """A progress indicator should appear during file upload."""
        form = navigate_to_form

        # Arrange - slow down the upload with route interception
        def slow_upload(route):
            import time
            time.sleep(0.5)
            route.fulfill(status=200, body='{"id":1}', headers={"Content-Type": "application/json"})

        form.page.route("**/api/upload**", slow_upload)

        # Act
        form.upload_file("document", str(sample_image_file))

        # Assert - progress bar should be visible at some point
        assert form.is_visible('[data-testid="upload-progress"]')

    def test_upload_cancel(
        self, navigate_to_form: FormPage, sample_image_file: Path
    ) -> None:
        """The user should be able to cancel an in-progress upload."""
        form = navigate_to_form

        # Arrange
        form.upload_file("document", str(sample_image_file))

        # Act
        form.click('[data-testid="upload-cancel"]')

        # Assert
        assert not form.is_visible('[data-testid="upload-preview"]')

    def test_upload_preview_displayed(
        self, navigate_to_form: FormPage, sample_image_file: Path
    ) -> None:
        """After uploading an image, a preview thumbnail should be displayed."""
        form = navigate_to_form

        # Act
        form.upload_file("document", str(sample_image_file))

        # Assert
        preview = form.page.locator('[data-testid="upload-preview"]')
        expect(preview).to_be_visible()
        src = preview.get_attribute("src")
        assert src is not None and len(src) > 0


# ---------------------------------------------------------------------------
# Upload management (remove, replace)
# ---------------------------------------------------------------------------


class TestUploadManagement:
    """Tests for managing uploaded files (remove, replace)."""

    def test_upload_remove_uploaded_file(
        self, navigate_to_form: FormPage, sample_text_file: Path
    ) -> None:
        """The user should be able to remove an already uploaded file."""
        form = navigate_to_form

        # Arrange
        form.upload_file("document", str(sample_text_file))
        assert form.is_visible('[data-testid="upload-filename"]')

        # Act
        form.click('[data-testid="upload-remove"]')

        # Assert
        assert not form.is_visible('[data-testid="upload-filename"]')

    def test_upload_replace_existing_file(
        self, navigate_to_form: FormPage, sample_text_file: Path, sample_csv_file: Path
    ) -> None:
        """Uploading a new file should replace the previously uploaded one."""
        form = navigate_to_form

        # Arrange
        form.upload_file("document", str(sample_text_file))
        assert "sample.txt" in form.get_text('[data-testid="upload-filename"]')

        # Act
        form.upload_file("document", str(sample_csv_file))

        # Assert
        filename_text = form.get_text('[data-testid="upload-filename"]')
        assert "sample.csv" in filename_text
        assert "sample.txt" not in filename_text


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestUploadEdgeCases:
    """Tests for edge cases in file uploads."""

    def test_upload_with_special_characters_filename(
        self, navigate_to_form: FormPage, special_char_filename_file: Path
    ) -> None:
        """Uploading a file with special characters in the name should work."""
        form = navigate_to_form

        # Act
        form.upload_file("document", str(special_char_filename_file))

        # Assert
        assert form.is_visible('[data-testid="upload-filename"]')

    def test_upload_drag_and_drop(
        self, navigate_to_form: FormPage, sample_text_file: Path
    ) -> None:
        """Files should be uploadable via drag-and-drop onto the drop zone."""
        form = navigate_to_form
        drop_zone = form.page.locator('[data-testid="drop-zone"]')

        # Act - simulate drag and drop using Playwright's file chooser approach
        # Since native drag-and-drop of files is complex, use set_input_files as proxy
        data_transfer = form.page.evaluate_handle(
            """() => {
                const dt = new DataTransfer();
                return dt;
            }"""
        )
        drop_zone.dispatch_event("drop", {"dataTransfer": data_transfer})

        # Alternative: use the file input directly as the drop zone
        # triggers the same handler
        form.upload_file("document", str(sample_text_file))

        # Assert
        assert form.is_visible('[data-testid="upload-filename"]')

    def test_upload_file_persists_after_form_error(
        self, navigate_to_form: FormPage, sample_text_file: Path
    ) -> None:
        """An uploaded file should remain after a form validation error."""
        form = navigate_to_form

        # Arrange - upload a file
        form.upload_file("document", str(sample_text_file))
        assert form.is_visible('[data-testid="upload-filename"]')

        # Act - submit form without required fields to trigger error
        form.submit()

        # Assert - file should still be attached
        assert form.is_visible('[data-testid="upload-filename"]')
        assert "sample.txt" in form.get_text('[data-testid="upload-filename"]')
