"""Unit tests for the dashboard theme configuration module."""

from src.dashboard.theme import (
    DARK_BACKGROUND,
    SECONDARY_BACKGROUND,
    TEXT_COLOR,
    PRIMARY_COLOR,
    GRID_COLOR,
    get_plotly_template,
    collapsible_section,
)


class TestThemeConstants:
    """Verify theme constants match .streamlit/config.toml values."""

    def test_dark_background_matches_config(self):
        assert DARK_BACKGROUND == "rgba(0,0,0,0)"

    def test_secondary_background_matches_config(self):
        assert SECONDARY_BACKGROUND == "#1a1a2e"

    def test_text_color_matches_config(self):
        assert TEXT_COLOR == "#e2e8f0"

    def test_primary_color_matches_config(self):
        assert PRIMARY_COLOR == "#6366f1"


class TestGetPlotlyTemplate:
    """Verify get_plotly_template returns correct dark theme layout."""

    def test_returns_dict(self):
        result = get_plotly_template()
        assert isinstance(result, dict)

    def test_uses_plotly_dark_template(self):
        result = get_plotly_template()
        assert result["template"] == "plotly_dark"

    def test_paper_bgcolor_dark(self):
        result = get_plotly_template()
        assert result["paper_bgcolor"] == "rgba(0,0,0,0)"

    def test_plot_bgcolor_dark(self):
        result = get_plotly_template()
        assert result["plot_bgcolor"] == "rgba(10, 15, 30, 0.5)"

    def test_font_color_high_contrast(self):
        result = get_plotly_template()
        assert result["font"]["color"] == "#e2e8f0"

    def test_font_size_readable(self):
        result = get_plotly_template()
        assert result["font"]["size"] >= 12

    def test_colorway_has_multiple_colors(self):
        result = get_plotly_template()
        assert len(result["colorway"]) >= 5

    def test_title_font_color(self):
        result = get_plotly_template()
        assert result["title"]["font"]["color"] == "#e2e8f0"

    def test_grid_colors_subtle(self):
        result = get_plotly_template()
        # Grid colors should use rgba with low opacity for subtlety
        assert "rgba" in result["xaxis"]["gridcolor"]
        assert "rgba" in result["yaxis"]["gridcolor"]


class TestCollapsibleSection:
    """Verify collapsible_section is a valid context manager."""

    def test_is_callable(self):
        assert callable(collapsible_section)

    def test_signature_has_title_and_expanded(self):
        import inspect
        sig = inspect.signature(collapsible_section)
        params = list(sig.parameters.keys())
        assert "title" in params
        assert "expanded" in params

    def test_expanded_defaults_to_true(self):
        import inspect
        sig = inspect.signature(collapsible_section)
        assert sig.parameters["expanded"].default is True
