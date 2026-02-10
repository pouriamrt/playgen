"""Form-specific fixtures for form interaction and validation tests."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

import pytest
from faker import Faker
from playwright.sync_api import Page

from config.settings import settings
from pages.form_page import FormPage
from pages.modal_page import ModalPage

fake = Faker()


# ---------------------------------------------------------------------------
# Authenticated page fixture (form-specific)
# ---------------------------------------------------------------------------


@pytest.fixture()
def form_page(authenticated_page: Page) -> FormPage:
    """Return a FormPage object backed by an authenticated browser page."""
    return FormPage(authenticated_page)


@pytest.fixture()
def modal_page(authenticated_page: Page) -> ModalPage:
    """Return a ModalPage object backed by an authenticated browser page."""
    return ModalPage(authenticated_page)


# ---------------------------------------------------------------------------
# Sample form data factories
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_form_data() -> dict[str, str]:
    """Generate a complete set of sample form data using Faker."""
    return {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.email(),
        "phone": fake.phone_number(),
        "password": fake.password(length=12, special_chars=True, digits=True, upper_case=True),
        "address": fake.street_address(),
        "city": fake.city(),
        "state": fake.state(),
        "zip_code": fake.zipcode(),
        "country": fake.country(),
        "company": fake.company(),
        "website": fake.url(),
        "description": fake.paragraph(nb_sentences=3),
        "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=80).strftime("%Y-%m-%d"),
    }


@pytest.fixture()
def minimal_form_data() -> dict[str, str]:
    """Generate minimal required form data."""
    return {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.email(),
    }


# ---------------------------------------------------------------------------
# File upload fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_text_file(tmp_path: Path) -> Path:
    """Create a temporary text file for upload testing."""
    file = tmp_path / "sample.txt"
    file.write_text("This is a sample text file for upload testing.")
    return file


@pytest.fixture()
def sample_image_file(tmp_path: Path) -> Path:
    """Create a minimal valid PNG file for upload testing."""
    file = tmp_path / "sample.png"
    # Minimal 1x1 pixel PNG
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
        b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
        b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    file.write_bytes(png_bytes)
    return file


@pytest.fixture()
def sample_pdf_file(tmp_path: Path) -> Path:
    """Create a minimal valid PDF file for upload testing."""
    file = tmp_path / "sample.pdf"
    pdf_content = (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n"
        b"0000000009 00000 n \n0000000058 00000 n \n"
        b"0000000115 00000 n \ntrailer<</Size 4/Root 1 0 R>>\n"
        b"startxref\n190\n%%EOF\n"
    )
    file.write_bytes(pdf_content)
    return file


@pytest.fixture()
def sample_csv_file(tmp_path: Path) -> Path:
    """Create a sample CSV file for upload testing."""
    file = tmp_path / "sample.csv"
    file.write_text("name,email,phone\nJohn Doe,john@example.com,555-1234\n")
    return file


@pytest.fixture()
def oversized_file(tmp_path: Path) -> Path:
    """Create a file that exceeds the typical upload size limit (11 MB)."""
    file = tmp_path / "oversized.bin"
    file.write_bytes(b"\x00" * (11 * 1024 * 1024))
    return file


@pytest.fixture()
def empty_file(tmp_path: Path) -> Path:
    """Create an empty file for upload testing."""
    file = tmp_path / "empty.txt"
    file.write_text("")
    return file


@pytest.fixture()
def special_char_filename_file(tmp_path: Path) -> Path:
    """Create a file with special characters in the filename."""
    file = tmp_path / "file with spaces & (special).txt"
    file.write_text("File with special characters in filename.")
    return file


@pytest.fixture()
def invalid_extension_file(tmp_path: Path) -> Path:
    """Create a file with an unsupported extension for upload testing."""
    file = tmp_path / "malicious.exe"
    file.write_text("This is not a real executable.")
    return file


# ---------------------------------------------------------------------------
# Form navigation helper
# ---------------------------------------------------------------------------


@pytest.fixture()
def navigate_to_form(form_page: FormPage):
    """Navigate to the form page and return the form page object."""
    form_page.navigate("/forms/create")
    form_page.wait_for_load()
    return form_page


@pytest.fixture()
def navigate_to_edit_form(form_page: FormPage):
    """Navigate to the edit form page."""
    form_page.navigate("/forms/edit/1")
    form_page.wait_for_load()
    return form_page


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _form_cleanup(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Auto-cleanup fixture to handle any post-test form state cleanup."""
    yield
    # If the test used the modal_page fixture, ensure modal is closed
    modal = request.node.funcargs.get("modal_page")
    if modal and modal.is_open():
        try:
            modal.close()
        except Exception:
            pass
