from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class BrowserOptions:
    headless: bool = True
    slow_mo: int = 0


@dataclass(frozen=True)
class Viewport:
    width: int = 1280
    height: int = 720


@dataclass(frozen=True)
class Settings:
    # URLs
    base_url: str = field(default_factory=lambda: os.getenv("BASE_URL", "http://localhost:3000"))
    api_url: str = field(default_factory=lambda: os.getenv("API_URL", "http://localhost:3000/api"))

    # Auth mode: "dev" skips login (target app bypasses auth), "standard" uses credentials
    auth_mode: str = field(default_factory=lambda: os.getenv("AUTH_MODE", "standard"))

    # Credentials (ignored when auth_mode is "dev")
    admin_user: str = field(default_factory=lambda: os.getenv("ADMIN_USER", "admin@example.com"))
    admin_pass: str = field(default_factory=lambda: os.getenv("ADMIN_PASS", "admin123"))
    test_user: str = field(default_factory=lambda: os.getenv("TEST_USER", "user@example.com"))
    test_pass: str = field(default_factory=lambda: os.getenv("TEST_PASS", "user123"))

    # Database
    db_connection: str = field(
        default_factory=lambda: os.getenv(
            "DB_CONNECTION", "postgresql://user:password@localhost:5432/testdb"
        )
    )

    # Timeouts (milliseconds)
    default_timeout: int = field(
        default_factory=lambda: int(os.getenv("DEFAULT_TIMEOUT", "10000"))
    )
    navigation_timeout: int = field(
        default_factory=lambda: int(os.getenv("NAVIGATION_TIMEOUT", "30000"))
    )

    # Browser
    browser: BrowserOptions = field(
        default_factory=lambda: BrowserOptions(
            headless=os.getenv("HEADLESS", "true").lower() == "true",
            slow_mo=int(os.getenv("SLOW_MO", "0")),
        )
    )

    # Viewport
    viewport: Viewport = field(
        default_factory=lambda: Viewport(
            width=int(os.getenv("VIEWPORT_WIDTH", "1280")),
            height=int(os.getenv("VIEWPORT_HEIGHT", "720")),
        )
    )

    # Artifacts
    screenshot_on_failure: bool = field(
        default_factory=lambda: os.getenv("SCREENSHOT_ON_FAILURE", "true").lower() == "true"
    )
    video_recording: str = field(
        default_factory=lambda: os.getenv("VIDEO_RECORDING", "off")
    )
    trace_recording: str = field(
        default_factory=lambda: os.getenv("TRACE_RECORDING", "off")
    )

    # Directories
    project_root: Path = PROJECT_ROOT
    screenshots_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "screenshots")
    videos_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "videos")
    traces_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "traces")
    reports_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "reports")

    # Analyzer / Code Generation
    source_code_dir: str = field(
        default_factory=lambda: os.getenv("SOURCE_CODE_DIR", "")
    )
    generated_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "generated")
    discovery_schema_path: Path = field(
        default_factory=lambda: PROJECT_ROOT / "generated" / "discovery.json"
    )

    def ensure_artifact_dirs(self) -> None:
        for d in (self.screenshots_dir, self.videos_dir, self.traces_dir, self.reports_dir):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
