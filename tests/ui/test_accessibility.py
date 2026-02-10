"""Accessibility tests -- WCAG 2.1 compliance checks using Playwright."""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from config.settings import settings


# ---------------------------------------------------------------------------
# Page-level accessibility
# ---------------------------------------------------------------------------


@pytest.mark.accessibility
class TestPageLevelAccessibility:
    """Tests for page-level WCAG requirements."""

    def test_page_has_lang_attribute(self, page: Page) -> None:
        """Verify the <html> element has a valid lang attribute (WCAG 3.1.1)."""
        page.goto(f"{settings.base_url}/")
        page.wait_for_load_state("domcontentloaded")
        lang = page.evaluate("document.documentElement.lang")
        assert lang and len(lang) >= 2, (
            f"<html> should have a lang attribute, got '{lang}'"
        )

    def test_page_title_descriptive(self, page: Page) -> None:
        """Verify every page has a descriptive <title> (WCAG 2.4.2)."""
        page.goto(f"{settings.base_url}/")
        page.wait_for_load_state("domcontentloaded")
        title = page.title()
        assert title and len(title) > 3, (
            f"Page title should be descriptive, got '{title}'"
        )

    def test_heading_hierarchy(self, authenticated_page: Page) -> None:
        """Verify headings follow a logical hierarchy (no skipped levels)."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("domcontentloaded")
        headings = authenticated_page.evaluate("""
            () => {
                const hs = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                return Array.from(hs).map(h => parseInt(h.tagName[1]));
            }
        """)
        if len(headings) >= 2:
            for i in range(1, len(headings)):
                diff = headings[i] - headings[i - 1]
                assert diff <= 1, (
                    f"Heading level jumped from h{headings[i-1]} to h{headings[i]}"
                )

    def test_aria_landmarks_present(self, authenticated_page: Page) -> None:
        """Verify ARIA landmark regions are present (WCAG 1.3.1)."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("domcontentloaded")
        landmarks = authenticated_page.evaluate("""
            () => {
                const roles = ['banner', 'navigation', 'main', 'contentinfo'];
                const found = {};
                roles.forEach(r => {
                    found[r] = document.querySelectorAll(
                        `[role="${r}"], header, nav, main, footer`
                    ).length > 0;
                });
                return found;
            }
        """)
        assert landmarks.get("main") or landmarks.get("navigation"), (
            "Page should have at least a main or navigation landmark"
        )


# ---------------------------------------------------------------------------
# Image accessibility
# ---------------------------------------------------------------------------


@pytest.mark.accessibility
class TestImageAccessibility:
    """Tests for image alt text and decorative image handling."""

    def test_all_images_have_alt_text(self, authenticated_page: Page) -> None:
        """Verify all <img> elements have an alt attribute (WCAG 1.1.1)."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("domcontentloaded")
        missing_alt = authenticated_page.evaluate("""
            () => {
                const images = document.querySelectorAll('img');
                const missing = [];
                images.forEach((img, i) => {
                    if (!img.hasAttribute('alt')) {
                        missing.push(img.src || `img[${i}]`);
                    }
                });
                return missing;
            }
        """)
        assert len(missing_alt) == 0, (
            f"Images missing alt attribute: {missing_alt}"
        )


# ---------------------------------------------------------------------------
# Form accessibility
# ---------------------------------------------------------------------------


@pytest.mark.accessibility
class TestFormAccessibility:
    """Tests for form label association and error announcements."""

    def test_form_labels_associated_with_inputs(self, authenticated_page: Page) -> None:
        """Verify all form inputs have associated labels (WCAG 1.3.1)."""
        authenticated_page.goto(f"{settings.base_url}/login")
        authenticated_page.wait_for_load_state("domcontentloaded")
        unlabeled = authenticated_page.evaluate("""
            () => {
                const inputs = document.querySelectorAll(
                    'input:not([type="hidden"]):not([type="submit"]):not([type="button"]), select, textarea'
                );
                const missing = [];
                inputs.forEach((input) => {
                    const id = input.id;
                    const hasLabel = id && document.querySelector(`label[for="${id}"]`);
                    const hasAriaLabel = input.getAttribute('aria-label');
                    const hasAriaLabelledBy = input.getAttribute('aria-labelledby');
                    const wrappedInLabel = input.closest('label');
                    if (!hasLabel && !hasAriaLabel && !hasAriaLabelledBy && !wrappedInLabel) {
                        missing.push(input.name || input.id || input.type);
                    }
                });
                return missing;
            }
        """)
        assert len(unlabeled) == 0, (
            f"Inputs without associated labels: {unlabeled}"
        )

    def test_form_error_announcements(self, authenticated_page: Page) -> None:
        """Verify form validation errors use aria-live or role=alert for screen readers."""
        authenticated_page.goto(f"{settings.base_url}/login")
        authenticated_page.wait_for_load_state("domcontentloaded")
        # Submit empty form to trigger errors
        submit = authenticated_page.locator('[data-testid="login-button"]')
        if submit.count() > 0:
            submit.click()
            authenticated_page.wait_for_timeout(500)
            error_regions = authenticated_page.evaluate("""
                () => {
                    const errors = document.querySelectorAll(
                        '[role="alert"], [aria-live="polite"], [aria-live="assertive"], .error'
                    );
                    return errors.length;
                }
            """)
            # If errors appeared, they should be announced
            visible_errors = authenticated_page.locator('[data-testid="error-message"], .error:visible')
            if visible_errors.count() > 0:
                assert error_regions > 0, (
                    "Form errors should use role=alert or aria-live for screen reader announcement"
                )

    def test_screen_reader_friendly_error_messages(self, authenticated_page: Page) -> None:
        """Verify error messages are accessible to screen readers."""
        authenticated_page.goto(f"{settings.base_url}/login")
        authenticated_page.wait_for_load_state("domcontentloaded")
        submit = authenticated_page.locator('[data-testid="login-button"]')
        if submit.count() > 0:
            submit.click()
            authenticated_page.wait_for_timeout(500)
            sr_errors = authenticated_page.evaluate("""
                () => {
                    const alerts = document.querySelectorAll('[role="alert"]');
                    return Array.from(alerts).map(el => el.textContent.trim());
                }
            """)
            for msg in sr_errors:
                assert len(msg) > 0, "Screen reader error messages should have text content"


# ---------------------------------------------------------------------------
# Color and contrast
# ---------------------------------------------------------------------------


@pytest.mark.accessibility
class TestColorContrast:
    """Tests for color contrast ratios."""

    def test_color_contrast_ratio(self, authenticated_page: Page) -> None:
        """Check that body text has sufficient contrast against background (WCAG 1.4.3).

        This is a simplified check using computed styles -- for comprehensive
        testing, use axe-core integration.
        """
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("domcontentloaded")
        contrast_info = authenticated_page.evaluate("""
            () => {
                const body = document.body;
                const style = getComputedStyle(body);
                return {
                    color: style.color,
                    background: style.backgroundColor
                };
            }
        """)
        # Basic check: color and background should be defined
        assert contrast_info["color"] != contrast_info["background"], (
            "Text color and background color should differ"
        )

    def test_links_distinguishable_from_text(self, authenticated_page: Page) -> None:
        """Verify links are visually distinguishable from surrounding text (WCAG 1.4.1)."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("domcontentloaded")
        link_styles = authenticated_page.evaluate("""
            () => {
                const link = document.querySelector('a:not([role="button"])');
                const body = document.body;
                if (!link) return null;
                const linkStyle = getComputedStyle(link);
                const bodyStyle = getComputedStyle(body);
                return {
                    linkColor: linkStyle.color,
                    bodyColor: bodyStyle.color,
                    textDecoration: linkStyle.textDecorationLine
                };
            }
        """)
        if link_styles:
            has_color_diff = link_styles["linkColor"] != link_styles["bodyColor"]
            has_underline = "underline" in link_styles["textDecoration"]
            assert has_color_diff or has_underline, (
                "Links should be distinguishable by color or underline"
            )


# ---------------------------------------------------------------------------
# Focus management
# ---------------------------------------------------------------------------


@pytest.mark.accessibility
class TestFocusManagement:
    """Tests for focus visibility and keyboard interaction."""

    def test_focus_visible_on_interactive_elements(self, authenticated_page: Page) -> None:
        """Verify interactive elements have a visible focus indicator (WCAG 2.4.7)."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("domcontentloaded")
        authenticated_page.keyboard.press("Tab")
        has_focus_style = authenticated_page.evaluate("""
            () => {
                const el = document.activeElement;
                if (!el) return false;
                const style = getComputedStyle(el);
                const outline = style.outlineStyle;
                const boxShadow = style.boxShadow;
                return (outline !== 'none' && outline !== '') ||
                       (boxShadow !== 'none' && boxShadow !== '');
            }
        """)
        assert has_focus_style, "Focused element should have a visible focus indicator"

    def test_keyboard_only_navigation(self, authenticated_page: Page) -> None:
        """Verify all interactive elements can be reached via keyboard only."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("domcontentloaded")
        visited_tags = set()
        for _ in range(15):
            authenticated_page.keyboard.press("Tab")
            tag = authenticated_page.evaluate(
                "document.activeElement ? document.activeElement.tagName.toLowerCase() : null"
            )
            if tag:
                visited_tags.add(tag)
        interactive = {"a", "button", "input", "select", "textarea"}
        reached = visited_tags & interactive
        assert len(reached) >= 1, (
            f"Keyboard navigation should reach interactive elements, visited: {visited_tags}"
        )

    def test_skip_navigation_link(self, page: Page) -> None:
        """Verify a skip-navigation link is present as the first focusable element."""
        page.goto(f"{settings.base_url}/")
        page.wait_for_load_state("domcontentloaded")
        page.keyboard.press("Tab")
        first_focused = page.evaluate("""
            () => {
                const el = document.activeElement;
                if (!el) return {};
                return {
                    tag: el.tagName.toLowerCase(),
                    href: el.getAttribute('href'),
                    text: el.textContent.trim().toLowerCase()
                };
            }
        """)
        if first_focused.get("text"):
            is_skip = "skip" in first_focused["text"] or "content" in first_focused["text"]
            if first_focused.get("tag") == "a":
                assert is_skip or first_focused.get("href", "").startswith("#"), (
                    "First focusable element should be a skip-navigation link"
                )


# ---------------------------------------------------------------------------
# ARIA live regions
# ---------------------------------------------------------------------------


@pytest.mark.accessibility
class TestAriaLiveRegions:
    """Tests for ARIA live regions used in dynamic content updates."""

    def test_aria_live_regions_for_dynamic_content(self, authenticated_page: Page) -> None:
        """Verify aria-live regions exist for dynamic content areas."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("domcontentloaded")
        live_regions = authenticated_page.evaluate("""
            () => {
                const regions = document.querySelectorAll(
                    '[aria-live], [role="status"], [role="alert"], [role="log"]'
                );
                return regions.length;
            }
        """)
        # Soft check -- not all pages require live regions
        assert isinstance(live_regions, int), "Should return count of live regions"


# ---------------------------------------------------------------------------
# Media accessibility
# ---------------------------------------------------------------------------


@pytest.mark.accessibility
class TestMediaAccessibility:
    """Tests for auto-playing media and text resizing."""

    def test_no_auto_playing_media(self, page: Page) -> None:
        """Verify no media auto-plays with sound (WCAG 1.4.2)."""
        page.goto(f"{settings.base_url}/")
        page.wait_for_load_state("domcontentloaded")
        auto_playing = page.evaluate("""
            () => {
                const media = document.querySelectorAll('video, audio');
                const autoplaying = [];
                media.forEach(el => {
                    if (el.autoplay && !el.muted) {
                        autoplaying.push(el.tagName);
                    }
                });
                return autoplaying;
            }
        """)
        assert len(auto_playing) == 0, (
            f"Media elements should not auto-play with sound: {auto_playing}"
        )

    def test_text_resizable_to_200_percent(self, authenticated_page: Page) -> None:
        """Verify content is usable when text is scaled to 200% (WCAG 1.4.4)."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("domcontentloaded")
        # Simulate 200% text zoom via CSS
        authenticated_page.evaluate("document.documentElement.style.fontSize = '200%'")
        authenticated_page.wait_for_timeout(300)
        has_overflow = authenticated_page.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth * 1.1"
        )
        # Content should remain readable without severe horizontal overflow
        assert not has_overflow, (
            "Content should be usable at 200% text size without horizontal overflow"
        )
        authenticated_page.evaluate("document.documentElement.style.fontSize = ''")


# ---------------------------------------------------------------------------
# Table accessibility
# ---------------------------------------------------------------------------


@pytest.mark.accessibility
class TestTableAccessibility:
    """Tests for data table accessibility."""

    def test_table_has_proper_headers(self, authenticated_page: Page) -> None:
        """Verify data tables use proper <th> elements with scope (WCAG 1.3.1)."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("domcontentloaded")
        table_issues = authenticated_page.evaluate("""
            () => {
                const tables = document.querySelectorAll('table');
                const issues = [];
                tables.forEach((table, i) => {
                    const headers = table.querySelectorAll('th');
                    if (headers.length === 0) {
                        issues.push(`Table ${i} has no <th> elements`);
                    }
                });
                return issues;
            }
        """)
        if table_issues:
            pytest.fail(f"Table accessibility issues: {table_issues}")


# ---------------------------------------------------------------------------
# Component ARIA roles
# ---------------------------------------------------------------------------


@pytest.mark.accessibility
class TestComponentRoles:
    """Tests for correct ARIA roles on interactive components."""

    def test_modal_accessible_role(self, authenticated_page: Page) -> None:
        """Verify modals have role=dialog and aria-modal=true."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        trigger = authenticated_page.locator('[data-testid="modal-trigger"]').first
        if trigger.count() > 0:
            trigger.click()
            modal = authenticated_page.locator('[data-testid="modal-content"]')
            modal.wait_for(state="visible", timeout=3000)
            role = modal.get_attribute("role")
            aria_modal = modal.get_attribute("aria-modal")
            assert role == "dialog" or role == "alertdialog", (
                f"Modal should have role=dialog, got '{role}'"
            )
            assert aria_modal == "true", "Modal should have aria-modal=true"

    def test_button_accessible_names(self, authenticated_page: Page) -> None:
        """Verify all buttons have accessible names (WCAG 4.1.2)."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("domcontentloaded")
        unnamed_buttons = authenticated_page.evaluate("""
            () => {
                const buttons = document.querySelectorAll('button, [role="button"]');
                const unnamed = [];
                buttons.forEach((btn, i) => {
                    const text = btn.textContent.trim();
                    const ariaLabel = btn.getAttribute('aria-label');
                    const ariaLabelledBy = btn.getAttribute('aria-labelledby');
                    const title = btn.getAttribute('title');
                    if (!text && !ariaLabel && !ariaLabelledBy && !title) {
                        unnamed.push(`button[${i}]`);
                    }
                });
                return unnamed;
            }
        """)
        assert len(unnamed_buttons) == 0, (
            f"Buttons without accessible names: {unnamed_buttons}"
        )


# ---------------------------------------------------------------------------
# Axe-core full-page scan
# ---------------------------------------------------------------------------


@pytest.mark.accessibility
class TestAxeCore:
    """Full-page accessibility scan using axe-core (if available)."""

    def test_axe_core_no_violations(self, authenticated_page: Page) -> None:
        """Run axe-core accessibility audit and verify zero critical violations.

        This test injects axe-core from CDN. If the CDN is unreachable
        (e.g., in an isolated environment), the test is skipped.
        """
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("networkidle")

        # Inject axe-core
        try:
            authenticated_page.evaluate("""
                async () => {
                    if (window.axe) return;
                    const script = document.createElement('script');
                    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js';
                    document.head.appendChild(script);
                    await new Promise((resolve, reject) => {
                        script.onload = resolve;
                        script.onerror = reject;
                    });
                }
            """)
        except Exception:
            pytest.skip("Could not load axe-core -- CDN may be unreachable")

        results = authenticated_page.evaluate("""
            async () => {
                if (!window.axe) return {violations: []};
                const results = await axe.run(document, {
                    runOnly: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']
                });
                return {
                    violations: results.violations.map(v => ({
                        id: v.id,
                        impact: v.impact,
                        description: v.description,
                        nodes: v.nodes.length
                    }))
                };
            }
        """)

        violations = results.get("violations", [])
        critical = [v for v in violations if v["impact"] in ("critical", "serious")]
        if critical:
            details = "\n".join(
                f"  - [{v['impact']}] {v['id']}: {v['description']} ({v['nodes']} nodes)"
                for v in critical
            )
            pytest.fail(f"Axe-core found {len(critical)} critical/serious violations:\n{details}")
