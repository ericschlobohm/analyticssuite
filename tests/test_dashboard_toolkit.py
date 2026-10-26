import pandas as pd
import plotly.graph_objects as go
import pytest

from snowflake_analytics_agents import dashboard_toolkit as tk


@pytest.fixture
def yearly():
    return pd.DataFrame(
        {"k": ["A", "A", "B", "B", "C", "C"], "year": [2022, 2024] * 3, "v": [100.0, 110.0, 100.0, 90.0, 50.0, 50.0]}
    )


def test_first_last_change_sorted_descending(yearly):
    s = tk.first_last_change(yearly, "v", key="k")
    assert list(s["k"]) == ["A", "C", "B"]
    assert s.set_index("k").loc["A", "pct_change"] == pytest.approx(10.0)
    assert {"v_2022", "v_2024", "abs_change"} <= set(s.columns)


def test_common_keys_drops_partial_entities():
    df = pd.DataFrame({"k": ["A", "A", "B"], "year": [2022, 2023, 2022]})
    assert set(tk.common_keys(df, ["k"])["k"]) == {"A"}


def test_indexed_lines_starts_at_100(yearly):
    fig = tk.indexed_lines(yearly, "k", "v", "t")
    assert all(trace.y[0] == pytest.approx(100.0) for trace in fig.data)


def test_choropleth_is_zero_centred():
    fig = tk.choropleth_change(pd.Series(["OR", "NY"]), pd.Series([3.0, -1.0]), "t")
    assert fig.data[0].zmin == -3.0 and fig.data[0].zmax == 3.0


def test_bar_extremes_colors_by_sign(yearly):
    s = tk.first_last_change(yearly, "v", key="k")
    fig = tk.bar_extremes(s, "k", "t", n=1)
    assert set(fig.data[0].marker.color) == {tk.UP_COLOR, tk.DOWN_COLOR}


def test_render_html_escapes_and_embeds_plotly_once():
    figs = [("<b>x</b>", go.Figure()), ("y", go.Figure())]
    page = tk.render_html("T&C", "sub", figs, tk.kpi_cards([("<k>", "v")]), "<p>n</p>")
    assert "T&amp;C" in page and "&lt;b&gt;x" in page and "&lt;k&gt;" in page
    assert page.count("plotly.js v") <= 1 or page.count("window.PlotlyConfig") >= 1
    assert "<p>n</p>" in page


def test_download_zip_uses_cache(tmp_path):
    (tmp_path / "a.csv").write_text("x")
    assert tk.download_zip("http://invalid.invalid/x.zip", tmp_path, marker_glob="*.csv") == tmp_path
