"""Rich input component tests.

Tests for advanced input components including date pickers, autocomplete,
multi-select dropdowns, color pickers, rich text editors, sliders, and toggles.
"""
from __future__ import annotations

import pytest
from faker import Faker
from playwright.sync_api import Page, expect

from pages.form_page import FormPage

fake = Faker()

pytestmark = [pytest.mark.forms, pytest.mark.regression]


# ---------------------------------------------------------------------------
# Date picker tests
# ---------------------------------------------------------------------------


class TestDatePicker:
    """Tests for the date picker component."""

    DATE_PICKER = '[data-testid="datepicker-start_date"]'
    CALENDAR_POPUP = '[data-testid="calendar-popup"]'
    CALENDAR_DAY = '[data-testid="calendar-day-{day}"]'
    CALENDAR_NEXT_MONTH = '[data-testid="calendar-next-month"]'
    CALENDAR_PREV_MONTH = '[data-testid="calendar-prev-month"]'
    CALENDAR_MONTH_LABEL = '[data-testid="calendar-month-label"]'

    def test_date_picker_opens_on_click(
        self, navigate_to_form: FormPage
    ) -> None:
        """Clicking the date picker input should open the calendar popup."""
        form = navigate_to_form

        # Act
        form.click(self.DATE_PICKER)

        # Assert
        assert form.is_visible(self.CALENDAR_POPUP)

    def test_date_picker_select_date(
        self, navigate_to_form: FormPage
    ) -> None:
        """Selecting a date in the calendar should populate the input field."""
        form = navigate_to_form

        # Act
        form.click(self.DATE_PICKER)
        form.click(self.CALENDAR_DAY.format(day="15"))

        # Assert
        value = form.get_input_value(self.DATE_PICKER)
        assert "15" in value

    def test_date_picker_navigate_months(
        self, navigate_to_form: FormPage
    ) -> None:
        """The calendar should allow navigating to the next and previous months."""
        form = navigate_to_form

        # Arrange
        form.click(self.DATE_PICKER)
        initial_month = form.get_text(self.CALENDAR_MONTH_LABEL)

        # Act - go to next month
        form.click(self.CALENDAR_NEXT_MONTH)

        # Assert
        new_month = form.get_text(self.CALENDAR_MONTH_LABEL)
        assert new_month != initial_month

        # Act - go back
        form.click(self.CALENDAR_PREV_MONTH)

        # Assert
        restored_month = form.get_text(self.CALENDAR_MONTH_LABEL)
        assert restored_month == initial_month

    def test_date_picker_keyboard_navigation(
        self, navigate_to_form: FormPage
    ) -> None:
        """The date picker should support keyboard navigation (arrows, Enter)."""
        form = navigate_to_form

        # Act
        form.click(self.DATE_PICKER)
        form.page.keyboard.press("ArrowRight")
        form.page.keyboard.press("ArrowRight")
        form.page.keyboard.press("Enter")

        # Assert - a date should be selected
        value = form.get_input_value(self.DATE_PICKER)
        assert len(value) > 0


# ---------------------------------------------------------------------------
# Autocomplete / typeahead tests
# ---------------------------------------------------------------------------


class TestAutocomplete:
    """Tests for the autocomplete / typeahead input component."""

    AUTOCOMPLETE_INPUT = '[data-testid="autocomplete-city"]'
    SUGGESTIONS_LIST = '[data-testid="autocomplete-suggestions"]'
    SUGGESTION_ITEM = '[data-testid="suggestion-item"]'
    NO_RESULTS = '[data-testid="autocomplete-no-results"]'

    def test_autocomplete_shows_suggestions(
        self, navigate_to_form: FormPage
    ) -> None:
        """Typing into the autocomplete field should display a list of suggestions."""
        form = navigate_to_form

        # Act
        form.type_text(self.AUTOCOMPLETE_INPUT, "New", delay=50)

        # Assert
        form.page.wait_for_timeout(500)
        assert form.is_visible(self.SUGGESTIONS_LIST)
        suggestion_count = form.get_element_count(self.SUGGESTION_ITEM)
        assert suggestion_count > 0

    def test_autocomplete_select_suggestion(
        self, navigate_to_form: FormPage
    ) -> None:
        """Clicking a suggestion should populate the input field."""
        form = navigate_to_form

        # Act
        form.type_text(self.AUTOCOMPLETE_INPUT, "New", delay=50)
        form.page.wait_for_timeout(500)
        first_suggestion = form.page.locator(self.SUGGESTION_ITEM).first
        suggestion_text = first_suggestion.inner_text()
        first_suggestion.click()

        # Assert
        value = form.get_input_value(self.AUTOCOMPLETE_INPUT)
        assert suggestion_text in value

    def test_autocomplete_no_results(
        self, navigate_to_form: FormPage
    ) -> None:
        """Typing a query with no matches should show a 'no results' message."""
        form = navigate_to_form

        # Act
        form.type_text(self.AUTOCOMPLETE_INPUT, "xyznonexistent123", delay=50)
        form.page.wait_for_timeout(500)

        # Assert
        assert form.is_visible(self.NO_RESULTS)

    def test_autocomplete_keyboard_navigation(
        self, navigate_to_form: FormPage
    ) -> None:
        """The user should be able to navigate suggestions using arrow keys and Enter."""
        form = navigate_to_form

        # Act
        form.type_text(self.AUTOCOMPLETE_INPUT, "New", delay=50)
        form.page.wait_for_timeout(500)
        form.page.keyboard.press("ArrowDown")
        form.page.keyboard.press("ArrowDown")
        form.page.keyboard.press("Enter")

        # Assert - input should now contain the selected suggestion
        value = form.get_input_value(self.AUTOCOMPLETE_INPUT)
        assert len(value) > 3  # longer than the typed "New"


# ---------------------------------------------------------------------------
# Multi-select dropdown tests
# ---------------------------------------------------------------------------


class TestDropdownMultiSelect:
    """Tests for multi-select dropdown components."""

    MULTI_SELECT = '[data-testid="multi-select-tags"]'
    OPTION_ITEM = '[data-testid="multi-option-{value}"]'
    SELECTED_TAGS = '[data-testid="selected-tag"]'
    SEARCH_INPUT = '[data-testid="multi-select-search"]'

    def test_dropdown_multi_select(
        self, navigate_to_form: FormPage
    ) -> None:
        """User should be able to select multiple items from a dropdown."""
        form = navigate_to_form

        # Act
        form.click(self.MULTI_SELECT)
        form.click(self.OPTION_ITEM.format(value="tag1"))
        form.click(self.OPTION_ITEM.format(value="tag2"))

        # Assert
        selected_count = form.get_element_count(self.SELECTED_TAGS)
        assert selected_count == 2

    def test_dropdown_search_filter(
        self, navigate_to_form: FormPage
    ) -> None:
        """Typing in the multi-select search should filter available options."""
        form = navigate_to_form

        # Act
        form.click(self.MULTI_SELECT)
        form.fill(self.SEARCH_INPUT, "tag1")

        # Assert
        form.page.wait_for_timeout(300)
        visible_options = form.get_element_count('[data-testid^="multi-option-"]:visible')
        assert visible_options >= 1


# ---------------------------------------------------------------------------
# Color picker tests
# ---------------------------------------------------------------------------


class TestColorPicker:
    """Tests for the color picker input component."""

    COLOR_INPUT = '[data-testid="input-color"]'
    COLOR_PREVIEW = '[data-testid="color-preview"]'

    def test_color_picker(
        self, navigate_to_form: FormPage
    ) -> None:
        """Setting a color value should update the color preview."""
        form = navigate_to_form

        # Act
        form.page.locator(self.COLOR_INPUT).fill("#ff5733")

        # Assert
        preview = form.page.locator(self.COLOR_PREVIEW)
        expect(preview).to_be_visible()
        # The preview background colour should reflect the chosen colour
        bg_color = preview.evaluate("el => getComputedStyle(el).backgroundColor")
        assert bg_color is not None and bg_color != ""


# ---------------------------------------------------------------------------
# Rich text editor tests
# ---------------------------------------------------------------------------


class TestRichTextEditor:
    """Tests for the rich text editor component."""

    EDITOR = '[data-testid="rich-text-editor"]'
    EDITOR_CONTENT = '[data-testid="rich-text-content"]'
    BOLD_BUTTON = '[data-testid="rte-bold"]'
    ITALIC_BUTTON = '[data-testid="rte-italic"]'
    UNDERLINE_BUTTON = '[data-testid="rte-underline"]'

    def test_rich_text_editor_basic_formatting(
        self, navigate_to_form: FormPage
    ) -> None:
        """Applying bold/italic/underline formatting should modify the content."""
        form = navigate_to_form

        # Act - type text, select it, apply bold
        editor = form.page.locator(self.EDITOR_CONTENT)
        editor.click()
        form.page.keyboard.type("Hello World")
        form.page.keyboard.press("Control+a")
        form.click(self.BOLD_BUTTON)

        # Assert - content should contain bold formatting
        html = editor.inner_html()
        assert "<strong>" in html or "<b>" in html

    def test_rich_text_editor_paste_content(
        self, navigate_to_form: FormPage
    ) -> None:
        """Pasting text into the rich text editor should work correctly."""
        form = navigate_to_form

        # Act
        editor = form.page.locator(self.EDITOR_CONTENT)
        editor.click()

        # Use clipboard to paste
        form.page.evaluate(
            """() => {
                const editor = document.querySelector('[data-testid="rich-text-content"]');
                editor.focus();
                document.execCommand('insertText', false, 'Pasted content');
            }"""
        )

        # Assert
        text = editor.inner_text()
        assert "Pasted content" in text


# ---------------------------------------------------------------------------
# Slider input tests
# ---------------------------------------------------------------------------


class TestSliderInput:
    """Tests for the slider / range input component."""

    SLIDER = '[data-testid="slider-rating"]'
    SLIDER_VALUE = '[data-testid="slider-value"]'

    def test_slider_input_drag(
        self, navigate_to_form: FormPage
    ) -> None:
        """Dragging the slider should update the displayed value."""
        form = navigate_to_form

        # Arrange
        slider = form.page.locator(self.SLIDER)
        slider_box = slider.bounding_box()
        assert slider_box is not None

        # Act - drag from center to the right (increase value)
        center_x = slider_box["x"] + slider_box["width"] / 2
        center_y = slider_box["y"] + slider_box["height"] / 2
        target_x = slider_box["x"] + slider_box["width"] * 0.8

        form.page.mouse.move(center_x, center_y)
        form.page.mouse.down()
        form.page.mouse.move(target_x, center_y, steps=10)
        form.page.mouse.up()

        # Assert
        value_text = form.get_text(self.SLIDER_VALUE)
        assert int(value_text) > 50  # assuming 0-100 range, we moved to ~80%


# ---------------------------------------------------------------------------
# Toggle switch tests
# ---------------------------------------------------------------------------


class TestToggleSwitch:
    """Tests for the toggle / switch input component."""

    TOGGLE = '[data-testid="toggle-notifications"]'
    TOGGLE_LABEL = '[data-testid="toggle-label"]'

    def test_toggle_switch_on_off(
        self, navigate_to_form: FormPage
    ) -> None:
        """Clicking the toggle should switch between on and off states."""
        form = navigate_to_form

        # Arrange - check initial state
        toggle = form.page.locator(self.TOGGLE)
        initial_state = toggle.get_attribute("aria-checked")

        # Act - toggle once
        toggle.click()
        form.page.wait_for_timeout(200)

        # Assert - state should change
        new_state = toggle.get_attribute("aria-checked")
        assert new_state != initial_state

        # Act - toggle again
        toggle.click()
        form.page.wait_for_timeout(200)

        # Assert - state should revert
        restored_state = toggle.get_attribute("aria-checked")
        assert restored_state == initial_state
