# QA Test Suite - Project Guide

## Overview
Playwright + pytest QA test suite using the Page Object Model pattern.

## Structure
- `config/settings.py` - Centralized settings via `Settings` dataclass, loaded from env vars
- `pages/` - Page Objects inheriting from `BasePage` (uses `data-testid` selectors)
- `tests/` - Test modules organized by feature area (auth, forms, crud, navigation, api)
- `utils/` - Helpers: `APIClient` for REST calls, `DatabaseHelper` for DB ops, `Faker`-based generators
- `conftest.py` (root) - Browser config, auth fixtures (`authenticated_page`, `admin_page`, `guest_page`), screenshot-on-failure hook
- `scripts/` - `run_tests.py` (CLI runner), `setup.py` (environment setup)

## Conventions
- Markers: `@pytest.mark.smoke`, `@pytest.mark.regression`, `@pytest.mark.critical`, plus feature markers (`auth`, `forms`, `crud`, `navigation`, `api`, `performance`, `accessibility`)
- Selectors: Prefer `data-testid` attributes via `page.get_by_test_id()`
- Settings: Use `from config.settings import settings` -- never hardcode URLs or credentials
- Page Objects: Instantiate with `page` fixture, e.g. `login = LoginPage(page)`
- Tests: Name files `test_<feature>.py`, classes `Test<Feature>`, methods `test_<behavior>`

## Running Tests
```bash
python scripts/run_tests.py --suite smoke --browser chromium
python -m pytest tests/ -m smoke --browser chromium -v
```
