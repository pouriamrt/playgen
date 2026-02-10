from __future__ import annotations

import string
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from faker import Faker
from playwright.sync_api import Page

fake = Faker()


def random_string(length: int = 10, chars: str = string.ascii_letters + string.digits) -> str:
    """Generate a random string of specified length."""
    import random

    return "".join(random.choices(chars, k=length))


def random_email(domain: str = "test.example.com") -> str:
    """Generate a random email address."""
    return f"{random_string(8).lower()}@{domain}"


def generate_fake_user() -> dict[str, str]:
    """Generate fake user data using Faker."""
    return {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.email(),
        "username": fake.user_name(),
        "password": fake.password(length=12),
        "phone": fake.phone_number(),
        "address": fake.address(),
    }


def wait_for_condition(
    condition: Callable[[], bool],
    timeout: float = 10.0,
    interval: float = 0.5,
    message: str = "Condition not met within timeout",
) -> None:
    """Wait until a callable condition returns True or timeout is reached."""
    end_time = time.time() + timeout
    while time.time() < end_time:
        if condition():
            return
        time.sleep(interval)
    raise TimeoutError(message)


def take_screenshot(page: Page, name: str, directory: str | Path = "screenshots") -> Path:
    """Capture a screenshot and return the file path."""
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = dir_path / f"{name}_{timestamp}.png"
    page.screenshot(path=str(filepath))
    return filepath


def format_date(dt: datetime | None = None, fmt: str = "%Y-%m-%d") -> str:
    """Format a datetime object to a string."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def generate_fake_address() -> dict[str, str]:
    """Generate fake address data."""
    return {
        "street": fake.street_address(),
        "city": fake.city(),
        "state": fake.state(),
        "zip_code": fake.zipcode(),
        "country": fake.country(),
    }


def generate_fake_text(sentences: int = 3) -> str:
    """Generate fake paragraph text."""
    return fake.paragraph(nb_sentences=sentences)


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    keepchars = ("-", "_", ".")
    return "".join(c if c.isalnum() or c in keepchars else "_" for c in name).strip("_")
