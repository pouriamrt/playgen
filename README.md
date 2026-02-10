# QA Test Suite

A comprehensive, production-grade QA test suite built with **Playwright** and **pytest**. It uses the **Page Object Model** (POM) pattern and supports cross-browser testing, parallel execution, CI/CD integration, and rich reporting.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
  - [Test execution workflow](#test-execution-workflow)
- [Directory Structure](#directory-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Tests](#running-tests)
  - [Using the CLI Runner](#using-the-cli-runner)
  - [Using pytest Directly](#using-pytest-directly)
  - [Running Specific Test Suites](#running-specific-test-suites)
  - [Cross-Browser Testing](#cross-browser-testing)
  - [Parallel Execution](#parallel-execution)
- [CLI Options Reference](#cli-options-reference)
- [Writing New Tests](#writing-new-tests)
  - [Test File Structure](#test-file-structure)
  - [Using Page Objects](#using-page-objects)
  - [Available Fixtures](#available-fixtures)
  - [Using Markers](#using-markers)
- [Page Object Model](#page-object-model)
  - [BasePage Methods](#basepage-methods)
  - [Creating a New Page Object](#creating-a-new-page-object)
- [Reports and Artifacts](#reports-and-artifacts)
- [CI/CD Integration](#cicd-integration)
  - [GitHub Actions](#github-actions)
  - [Nightly Regression](#nightly-regression)
- [Docker Usage](#docker-usage)
- [Utilities](#utilities)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Project Overview

This test suite provides end-to-end testing for web applications with the following capabilities:

- **Authentication & authorization** testing (login, registration, roles, sessions)
- **Form interaction & validation** (inputs, dropdowns, file uploads, client/server validation)
- **CRUD operations** (create, read, update, delete with data verification)
- **Navigation & UI components** (routing, menus, modals, responsive design)
- **API integration** (REST endpoint verification alongside UI tests)
- **Performance** (page load times, Core Web Vitals)
- **Accessibility** (ARIA compliance, keyboard navigation)

All tests run against **Chromium**, **Firefox**, and **WebKit** via Playwright.

---

## Architecture

```
                     +-------------------+
                     |   pytest runner    |
                     +--------+----------+
                              |
                   +----------+----------+
                   |                     |
            +------+------+      +------+------+
            |  conftest.py |      |   markers   |
            |  (fixtures)  |      | smoke/regr. |
            +------+------+      +-------------+
                   |
         +---------+---------+
         |                   |
   +-----+-----+      +-----+-----+
   | Page Objects|      |  Utilities |
   | (pages/)   |      | (utils/)   |
   +-----+-----+      +-----+-----+
         |                   |
   +-----+-----+      +-----+-----+
   |  BasePage  |      | APIClient  |
   | (common    |      | DBHelper   |
   |  actions)  |      | Faker      |
   +------------+      +------------+
```

- **Page Objects** encapsulate page-specific selectors and actions
- **Fixtures** in `conftest.py` handle browser setup, authentication, and cleanup
- **Markers** categorize tests into suites (smoke, regression, etc.)
- **Utilities** provide API, database, and data generation helpers

### Test execution workflow

![QA Test Suite workflow](qa_test_suite_workflow.png)

---

## Directory Structure

```
QA_test_suite/
|-- config/
|   |-- __init__.py
|   +-- settings.py          # Centralized settings (env vars, paths, timeouts)
|
|-- pages/
|   |-- __init__.py           # Exports all page objects
|   |-- base_page.py          # BasePage with common methods
|   |-- login_page.py         # LoginPage
|   |-- register_page.py      # RegisterPage
|   |-- dashboard_page.py     # DashboardPage
|   |-- profile_page.py       # ProfilePage
|   |-- settings_page.py      # SettingsPage
|   |-- form_page.py          # FormPage
|   |-- table_page.py         # TablePage
|   |-- modal_page.py         # ModalPage
|   |-- navigation_page.py    # NavigationPage
|   +-- search_results_page.py # SearchResultsPage
|
|-- tests/
|   |-- __init__.py
|   |-- conftest.py            # Test-level fixtures (fake_user, unique_email)
|   |-- test_auth.py           # Authentication tests
|   |-- test_forms.py          # Form interaction tests
|   |-- test_crud.py           # CRUD operation tests
|   |-- test_navigation.py     # Navigation and UI tests
|   +-- test_api.py            # API integration tests
|
|-- utils/
|   |-- __init__.py
|   |-- api_client.py          # REST API client wrapper
|   |-- database.py            # Database helper (PostgreSQL)
|   +-- helpers.py             # Faker generators, utilities
|
|-- scripts/
|   |-- run_tests.py           # CLI test runner
|   +-- setup.py               # Environment setup script
|
|-- docker/
|   |-- Dockerfile             # Docker image for test execution
|   +-- docker-compose.yml     # Docker Compose services
|
|-- .github/workflows/
|   |-- qa-tests.yml           # CI pipeline (push, PR, manual)
|   +-- nightly-regression.yml # Nightly full regression
|
|-- reports/                   # Generated test reports (gitignored)
|-- screenshots/               # Failure screenshots (gitignored)
|-- videos/                    # Video recordings (gitignored)
|-- traces/                    # Playwright traces (gitignored)
|
|-- conftest.py                # Root conftest (browser, auth, hooks)
|-- pyproject.toml             # Project config, dependencies, pytest settings
|-- .env.example               # Example environment configuration
|-- CLAUDE.md                  # AI assistant project guide
+-- README.md                  # This file
```

---

## Prerequisites

- **Python 3.10+** (3.11 recommended)
- **[uv](https://docs.astral.sh/uv/)** - Fast Python package manager
- **Node.js** (optional, required only if Playwright needs to download browsers with system deps)
- **Git**

---

## Installation

### Quick Setup (recommended)

```bash
# Clone the repository
git clone <repository-url>
cd QA_test_suite

# Run the automated setup
python scripts/setup.py
```

The setup script will:
1. Install Python dependencies from `pyproject.toml`
2. Install Playwright browsers (Chromium, Firefox, WebKit)
3. Create a `.env` file from `.env.example` if missing
4. Verify the environment is ready

### Manual Setup

```bash
# Install dependencies
uv sync

# Install dev dependencies (ruff, mypy)
uv sync --extra dev

# Install Playwright browsers with system dependencies
uv run python -m playwright install --with-deps

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings
```

### Install Specific Browsers Only

```bash
# Install only Chromium
python scripts/setup.py --browsers chromium

# Skip browser installation entirely
python scripts/setup.py --skip-browsers
```

---

## Configuration

All configuration is managed through environment variables. Copy `.env.example` to `.env` and customize:

| Variable | Default | Description |
|---|---|---|
| `BASE_URL` | `http://localhost:3000` | Application base URL |
| `API_URL` | `http://localhost:3000/api` | API base URL |
| `ADMIN_USER` | `admin@example.com` | Admin account email |
| `ADMIN_PASS` | `admin123` | Admin account password |
| `TEST_USER` | `user@example.com` | Standard test user email |
| `TEST_PASS` | `user123` | Standard test user password |
| `DB_CONNECTION` | `postgresql://...` | Database connection string |
| `HEADLESS` | `true` | Run browsers in headless mode |
| `SLOW_MO` | `0` | Slow down actions by N ms (debugging) |
| `DEFAULT_TIMEOUT` | `10000` | Default element timeout (ms) |
| `NAVIGATION_TIMEOUT` | `30000` | Page navigation timeout (ms) |
| `VIEWPORT_WIDTH` | `1280` | Browser viewport width |
| `VIEWPORT_HEIGHT` | `720` | Browser viewport height |
| `SCREENSHOT_ON_FAILURE` | `true` | Capture screenshot on test failure |
| `VIDEO_RECORDING` | `off` | Record video (`on`/`off`) |
| `TRACE_RECORDING` | `off` | Record Playwright traces (`on`/`off`) |

---

## Running Tests

### Using the CLI Runner

The `scripts/run_tests.py` script provides a convenient CLI:

```bash
# Run smoke tests with Chromium (default)
python scripts/run_tests.py

# Run smoke tests in headed mode (see the browser)
python scripts/run_tests.py --suite smoke --browser chromium --headed

# Run regression tests with Firefox
python scripts/run_tests.py --suite regression --browser firefox

# Run full suite across all browsers
python scripts/run_tests.py --suite full --browser all

# Run with parallel workers
python scripts/run_tests.py --suite regression --workers 4

# Override base URL for staging
python scripts/run_tests.py --suite smoke --base-url https://staging.example.com

# Enable tracing and video on failure
python scripts/run_tests.py --suite smoke --tracing --video

# Run with Allure reporting
python scripts/run_tests.py --suite regression --report allure

# Filter tests by keyword
python scripts/run_tests.py --suite full -k "login or register"
```

### Using pytest Directly

```bash
# Basic run
python -m pytest tests/ -v

# Run with a specific marker
python -m pytest tests/ -m smoke --browser chromium -v

# Run a specific test file
python -m pytest tests/test_auth.py -v

# Run a specific test class
python -m pytest tests/test_auth.py::TestLogin -v

# Run a specific test method
python -m pytest tests/test_auth.py::TestLogin::test_valid_login -v

# Run with keyword expression
python -m pytest tests/ -k "login and not social" -v

# Run in parallel (4 workers)
python -m pytest tests/ -n 4 -v
```

### Running Specific Test Suites

```bash
# Smoke tests (quick, critical paths only)
python -m pytest tests/ -m smoke -v

# Regression tests (comprehensive)
python -m pytest tests/ -m regression -v

# Critical business functionality
python -m pytest tests/ -m critical -v

# Feature-specific suites
python -m pytest tests/ -m auth -v        # Authentication tests
python -m pytest tests/ -m forms -v       # Form tests
python -m pytest tests/ -m crud -v        # CRUD tests
python -m pytest tests/ -m navigation -v  # Navigation tests
python -m pytest tests/ -m api -v         # API tests
python -m pytest tests/ -m performance -v # Performance tests
```

### Cross-Browser Testing

```bash
# Single browser
python -m pytest tests/ --browser chromium -v
python -m pytest tests/ --browser firefox -v
python -m pytest tests/ --browser webkit -v

# Multiple browsers in one run
python -m pytest tests/ --browser chromium --browser firefox --browser webkit -v
```

### Parallel Execution

```bash
# Run with 4 parallel workers
python -m pytest tests/ -n 4 -v

# Auto-detect CPU count
python -m pytest tests/ -n auto -v
```

---

## CLI Options Reference

| Option | Values | Default | Description |
|---|---|---|---|
| `--suite` | smoke, regression, full, auth, forms, crud, navigation, api, performance, critical | smoke | Test suite to run |
| `--browser` | chromium, firefox, webkit, all | chromium | Browser to use |
| `--headed` | flag | false | Show browser window |
| `--workers` | integer | 1 | Parallel worker count |
| `--base-url` | URL string | from .env | Override base URL |
| `--report` | html, allure, both | html | Report format |
| `--timeout` | seconds | 30 | Test timeout |
| `--retries` | integer | 0 | Retry count for flaky tests |
| `--tracing` | flag | false | Enable Playwright tracing |
| `--video` | flag | false | Enable video recording |
| `-v` | flag | false | Verbose output |
| `-k` | expression | none | pytest keyword filter |

---

## Writing New Tests

### Test File Structure

Create test files in `tests/` following the naming convention `test_<feature>.py`:

```python
"""Tests for the user profile feature."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from pages import ProfilePage


@pytest.mark.smoke
@pytest.mark.regression
class TestProfileDisplay:
    """Tests for viewing user profile information."""

    def test_profile_shows_username(self, authenticated_page: Page) -> None:
        """Verify the profile page displays the logged-in username."""
        profile = ProfilePage(authenticated_page)
        profile.navigate_to_profile()
        expect(profile.locator(ProfilePage.USERNAME_DISPLAY)).to_be_visible()

    def test_profile_shows_email(self, authenticated_page: Page) -> None:
        """Verify the profile page displays the user email."""
        profile = ProfilePage(authenticated_page)
        profile.navigate_to_profile()
        expect(profile.locator(ProfilePage.EMAIL_DISPLAY)).to_be_visible()


@pytest.mark.regression
class TestProfileEdit:
    """Tests for editing user profile."""

    def test_update_display_name(self, authenticated_page: Page, fake_user: dict) -> None:
        """Verify the user can update their display name."""
        profile = ProfilePage(authenticated_page)
        profile.navigate_to_profile()
        profile.update_display_name(fake_user["first_name"])
        expect(profile.locator(ProfilePage.SUCCESS_MESSAGE)).to_be_visible()
```

### Using Page Objects

Page objects encapsulate page-specific selectors and actions:

```python
from pages import LoginPage, DashboardPage

def test_login_flow(page: Page) -> None:
    login = LoginPage(page)
    login.navigate_to_login()
    login.login("user@example.com", "password")

    dashboard = DashboardPage(page)
    assert dashboard.is_dashboard_loaded()
```

### Available Fixtures

| Fixture | Scope | Description |
|---|---|---|
| `page` | function | Fresh Playwright page with tracing support |
| `authenticated_page` | function | Page logged in as standard test user |
| `admin_page` | function | Page logged in as admin user |
| `guest_page` | function | Page with no authentication |
| `api_client` | session | REST API client instance |
| `db_cleanup` | function | Database helper with auto-disconnect |
| `fake_user` | function | Dict of random user data (Faker) |
| `unique_email` | function | Random email for test isolation |
| `sample_text` | function | Random paragraph text |

### Using Markers

Apply markers to categorize tests for suite selection:

```python
@pytest.mark.smoke           # Quick critical path tests
@pytest.mark.regression      # Full regression coverage
@pytest.mark.critical        # Critical business features
@pytest.mark.auth            # Authentication tests
@pytest.mark.forms           # Form interaction tests
@pytest.mark.crud            # CRUD operation tests
@pytest.mark.navigation      # Navigation tests
@pytest.mark.api             # API integration tests
@pytest.mark.performance     # Performance tests
@pytest.mark.accessibility   # Accessibility tests
@pytest.mark.slow            # Long-running tests
```

Multiple markers can be combined:

```python
@pytest.mark.smoke
@pytest.mark.auth
@pytest.mark.critical
def test_login_with_valid_credentials(self, page: Page) -> None:
    ...
```

---

## Page Object Model

### BasePage Methods

All page objects inherit from `BasePage`, which provides:

| Category | Method | Description |
|---|---|---|
| **Navigation** | `navigate(path)` | Go to a URL path relative to base URL |
| | `wait_for_load()` | Wait for network idle |
| | `get_title()` | Get page title |
| | `get_current_url()` | Get current URL |
| **Interaction** | `click(selector)` | Click an element |
| | `fill(selector, value)` | Clear and fill an input |
| | `select_option(selector, ...)` | Select from a dropdown |
| | `check(selector)` | Check a checkbox |
| | `uncheck(selector)` | Uncheck a checkbox |
| | `type_text(selector, text)` | Type character by character |
| | `hover(selector)` | Hover over an element |
| **State** | `is_visible(selector)` | Check element visibility |
| | `is_enabled(selector)` | Check if element is enabled |
| | `is_checked(selector)` | Check if checkbox is checked |
| | `get_text(selector)` | Get inner text |
| | `get_input_value(selector)` | Get input value |
| | `get_attribute(selector, attr)` | Get attribute value |
| | `get_element_count(selector)` | Count matching elements |
| **Waiting** | `wait_for_selector(selector)` | Wait for element state |
| | `wait_for_navigation(url)` | Wait for URL change |
| | `wait_for_hidden(selector)` | Wait for element to hide |
| **Locators** | `locator(selector)` | Get a Playwright Locator |
| | `get_by_test_id(id)` | Get by `data-testid` |
| | `get_by_role(role)` | Get by ARIA role |
| | `get_by_text(text)` | Get by text content |

### Creating a New Page Object

```python
from __future__ import annotations

from playwright.sync_api import Page

from pages.base_page import BasePage


class ProductPage(BasePage):
    """Page Object for the Product detail page."""

    # Selectors (use data-testid)
    PRODUCT_TITLE = '[data-testid="product-title"]'
    PRODUCT_PRICE = '[data-testid="product-price"]'
    ADD_TO_CART = '[data-testid="add-to-cart-button"]'
    QUANTITY_INPUT = '[data-testid="quantity-input"]'

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.path = "/products"

    def navigate_to_product(self, product_id: str) -> None:
        self.navigate(f"{self.path}/{product_id}")

    def get_product_title(self) -> str:
        return self.get_text(self.PRODUCT_TITLE)

    def get_product_price(self) -> str:
        return self.get_text(self.PRODUCT_PRICE)

    def add_to_cart(self, quantity: int = 1) -> None:
        self.fill(self.QUANTITY_INPUT, str(quantity))
        self.click(self.ADD_TO_CART)
```

Then register it in `pages/__init__.py`.

---

## Reports and Artifacts

### HTML Reports

After a test run, an HTML report is generated at `reports/report.html`. Open it in any browser:

```bash
# macOS
open reports/report.html

# Linux
xdg-open reports/report.html

# Windows
start reports/report.html
```

### Allure Reports

To use Allure reporting:

```bash
# Run tests with Allure
python scripts/run_tests.py --report allure

# Generate and open Allure report (requires allure CLI)
allure serve reports/allure-results
```

### Screenshots

Failure screenshots are saved automatically to `screenshots/FAIL_<test_name>.png` when `SCREENSHOT_ON_FAILURE=true`.

### Videos

When `VIDEO_RECORDING=on`, browser session videos are saved to `videos/`.

### Traces

When `TRACE_RECORDING=on`, Playwright traces are saved to `traces/` on failure. View traces with:

```bash
python -m playwright show-trace traces/FAIL_test_name.zip
```

---

## CI/CD Integration

### GitHub Actions

Two workflow files are included:

**`qa-tests.yml`** - Main CI pipeline:

| Trigger | Behavior |
|---|---|
| Push to `main`/`develop` | Run smoke tests (Chromium), then full regression on `main` (all browsers) |
| Pull Request | Run smoke tests (Chromium) |
| Manual dispatch | Choose suite, browser, and base URL |

**Features:**
- uv dependency caching
- Playwright browser caching
- Test report artifact uploads
- Screenshot and trace uploads on failure
- Video uploads for regression runs
- Browser matrix strategy (Chromium, Firefox, WebKit)

### Nightly Regression

**`nightly-regression.yml`** runs the full test suite every night at 2:00 AM UTC across all browsers with:
- Automatic retries (2 per failed test)
- Video and trace recording enabled
- Summary reporting
- Configurable Slack notifications (uncomment in workflow)

### Manual Dispatch

Trigger a run from the GitHub Actions UI:

1. Go to **Actions** > **QA Tests**
2. Click **Run workflow**
3. Select suite, browser, and optionally override the base URL

---

## Docker Usage

### Build the Image

```bash
docker build -f docker/Dockerfile -t qa-test-suite .
```

### Run Tests with Docker

```bash
# Run smoke tests (default)
docker run --rm -v $(pwd)/reports:/app/reports qa-test-suite

# Run regression tests
docker run --rm -v $(pwd)/reports:/app/reports qa-test-suite \
  tests/ -m regression --browser chromium -v

# Run with a custom base URL
docker run --rm -e BASE_URL=https://staging.example.com \
  -v $(pwd)/reports:/app/reports qa-test-suite
```

### Docker Compose

The `docker/docker-compose.yml` provides pre-configured services:

```bash
# Run smoke tests
docker compose -f docker/docker-compose.yml up smoke

# Run regression tests
docker compose -f docker/docker-compose.yml up regression

# Run all browsers
docker compose -f docker/docker-compose.yml up all-browsers

# Override base URL
BASE_URL=https://staging.example.com docker compose -f docker/docker-compose.yml up smoke
```

Reports, screenshots, videos, and traces are mounted to the host automatically.

---

## Utilities

### API Client

Use `APIClient` for backend verification alongside UI tests:

```python
def test_user_creation_reflected_in_api(
    self, authenticated_page: Page, api_client: APIClient
) -> None:
    # ... create user via UI ...
    response = api_client.get("/users?email=new@example.com")
    api_client.assert_status(response, 200)
```

### Database Helper

Use `DatabaseHelper` for direct DB verification (requires `psycopg2-binary`):

```python
def test_data_persisted_to_db(self, page: Page, db_cleanup) -> None:
    # ... perform action via UI ...
    result = db_cleanup.fetch_one(
        "SELECT * FROM users WHERE email = %s",
        ("new@example.com",),
    )
    assert result is not None
```

### Fake Data Generators

```python
from utils.helpers import generate_fake_user, random_email, random_string

user = generate_fake_user()  # Dict with first_name, last_name, email, ...
email = random_email()        # Random test email
text = random_string(20)      # Random alphanumeric string
```

---

## Troubleshooting

### Playwright browsers not installed

```
Error: Executable doesn't exist at ...
```

**Fix:** Install browsers with system dependencies:
```bash
python -m playwright install --with-deps
```

### Tests timeout immediately

**Likely cause:** The application under test is not running at `BASE_URL`.

**Fix:** Start the application, then verify:
```bash
curl http://localhost:3000
```

Or override the URL:
```bash
python scripts/run_tests.py --base-url https://your-app-url.com
```

### Permission denied on Linux/CI

```
Error: Failed to launch browser
```

**Fix:** Install system dependencies:
```bash
python -m playwright install-deps
```

### Tests pass locally but fail in CI

- Ensure `HEADLESS=true` in CI
- Check that the base URL is accessible from the CI runner
- Increase timeouts for CI: `--timeout 60`
- Review screenshots and traces in the CI artifacts

### Import errors

```
ModuleNotFoundError: No module named 'pages'
```

**Fix:** Sync the project dependencies:
```bash
uv sync
```

### Video/trace files not generated

Ensure the environment variables are set:
```bash
export VIDEO_RECORDING=on
export TRACE_RECORDING=on
```

Or use CLI flags:
```bash
python scripts/run_tests.py --video --tracing
```

---

## Contributing

1. **Branch naming:** `feature/<name>`, `fix/<name>`, `test/<name>`
2. **Test naming:** `test_<feature>.py` files, `Test<Feature>` classes, `test_<behavior>` methods
3. **Markers:** Always apply at least `@pytest.mark.smoke` or `@pytest.mark.regression`
4. **Page Objects:** Create page objects for new pages; never put selectors directly in tests
5. **Selectors:** Use `data-testid` attributes exclusively
6. **Settings:** Use `from config.settings import settings`; never hardcode URLs or credentials
7. **Linting:** Run `ruff check .` before committing
8. **Type checking:** Run `mypy .` to verify type annotations

---

*Built with [Playwright](https://playwright.dev/python/) and [pytest](https://docs.pytest.org/).*
