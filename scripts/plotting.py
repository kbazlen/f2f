
"""Plotting helpers used by the Quarto report."""

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_SHAPEFILE = (
    PROJECT_ROOT
    / "data"
    / "cb_2018_us_state_500k 2"
    / "cb_2018_us_state_500k.shp"
)
WESTERN_STATES = {
    "AZ", "CA", "CO", "ID", "KS", "MT", "ND", "NE", "NM",
    "NV", "OK", "OR", "SD", "TX", "UT", "WA", "WY",
}


def _load_western_states() -> gpd.GeoDataFrame:
    states = gpd.read_file(STATE_SHAPEFILE).to_crs("EPSG:4326")
    return states[states["STUSPS"].isin(WESTERN_STATES)]


def plot_site_location(lat: float, lon: float, *, title: str | None = None, ax=None):
    """Plot one monitoring-site location over western-state outlines."""
    if ax is None:
        _, ax = plt.subplots(figsize=(4, 4))
    _load_western_states().boundary.plot(ax=ax, color="black", linewidth=0.5)
    ax.scatter(lon, lat, marker="*", s=140, c="gold", edgecolors="black", zorder=3)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    if title is not None:
        ax.set_title(title)
    return ax


def plot_fire_locations(
    fire_locations: pd.DataFrame,
    high_severity_locations: pd.DataFrame | None = None,
    marker_size: float = 10,
    title: str | None = None,
    label: str = "All fires",
    ax=None,
):
    """Scatter fire lat/lon over the western-state outlines.

    Parameters
    ----------
    fire_locations : pandas.DataFrame
        Must have `lat` and `lon` columns, e.g. from
        `data_process.get_fires_above_burn_threshold`. Plotted in blue.
    high_severity_locations : pandas.DataFrame, optional
        Must have `lat` and `lon` columns, e.g. from
        `data_process.get_fires_above_high_severity_threshold`. Plotted in red,
        on top of `fire_locations`.
    marker_size : float, default 10
        Fixed marker size for both `fire_locations` and `high_severity_locations` points.
    title : str, optional
        Title to display above the plot.
    label : str, default "All fires"
        Legend label for the `fire_locations` scatter.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure/axes is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))
    _load_western_states().boundary.plot(ax=ax, color="black", linewidth=0.5)
    ax.scatter(
        fire_locations["lon"],
        fire_locations["lat"],
        s=marker_size,
        c="tab:blue",
        alpha=0.6,
        label=label,
    )
    if high_severity_locations is not None:
        ax.scatter(
            high_severity_locations["lon"],
            high_severity_locations["lat"],
            s=marker_size,
            c="firebrick",
            alpha=0.6,
            label="High severity",
        )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    if title is not None:
        ax.set_title(title)
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5))
    return ax


def plot_single_pre_fire_obs_distribution(
    values: pd.Series,
    parameter: str,
    *,
    bins: int = 30,
    rwidth: float = 0.6,
    exclude_zero: bool = True,
    ax=None,
):
    """Histogram for a single parameter's pre-fire observation counts.

    Parameters
    ----------
    values : pandas.Series
        Per-site/per-fire observation counts for the parameter.
    parameter : str
        Parameter key used in the plot title and label.
    bins : int, default 30
        Number of histogram bins.
    rwidth : float, default 0.6
        Relative bar width within each bin.
    exclude_zero : bool, default True
        Drop zero-count events before plotting and annotate how many were omitted.
    ax : matplotlib.axes.Axes, optional
        Axes to draw into. When omitted, a new figure/axes is created (and
        tight_layout is applied); when given, the caller owns layout.

    Returns
    -------
    matplotlib.figure.Figure
    """
    owns_figure = ax is None
    if owns_figure:
        fig, ax = plt.subplots(figsize=(7, 4))
    else:
        fig = ax.figure
    values = values.copy()
    n_zero = 0
    if exclude_zero:
        n_zero = int((values == 0).sum())
        values = values[values > 0]

    ax.hist(values, bins=bins, rwidth=rwidth, color="tab:blue", edgecolor="black")

    if exclude_zero:
        ax.text(
            0.97,
            0.95,
            f"n=0: {n_zero}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=8,
            bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.8),
        )

    ax.set_title(f"{parameter} pre-fire observations")
    ax.set_xlabel("Pre-fire observations")
    ax.set_ylabel("Number of sites")
    if owns_figure:
        fig.tight_layout()
    return fig


def render_pre_fire_histograms(
    values_by_parameter: dict[str, pd.Series],
    *,
    title_suffix: str = "pre-fire observations",
    xlabel: str = "Pre-fire observations",
    ylabel: str = "Number of sites",
) -> dict[str, str]:
    """Render one histogram per parameter, base64-encoded as a PNG.

    Pre-rendering every parameter once lets an HTML dropdown swap between
    them client-side without re-running the analysis on each selection.
    """
    import base64
    import io

    encoded = {}
    for parameter, values in values_by_parameter.items():
        fig = plot_single_pre_fire_obs_distribution(values, parameter)
        fig.axes[0].set_title(f"{parameter} {title_suffix}")
        fig.axes[0].set_xlabel(xlabel)
        fig.axes[0].set_ylabel(ylabel)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        encoded[parameter] = base64.b64encode(buf.getvalue()).decode("ascii")
    return encoded


def render_parameter_dropdown_html(
    encoded_plots: dict[str, str],
    *,
    id_prefix: str,
    default_parameter: str,
) -> str:
    """Build a `<select>` + inline-JS block that swaps between pre-rendered PNGs.

    HTML-only: the swap relies on JavaScript, which has no PDF equivalent.
    Pair with `render_parameter_grid_figure` for the static PDF fallback.
    """
    import json

    select_id = f"{id_prefix}-param-select"
    container_id = f"{id_prefix}-plot-container"
    options = "\n".join(
        f'<option value="{param}"{" selected" if param == default_parameter else ""}>{param}</option>'
        for param in encoded_plots
    )
    return f'''
<div style="margin-bottom: 0.75rem;">
  <label for="{select_id}">Parameter:</label>
  <select id="{select_id}">
    {options}
  </select>
</div>
<div id="{container_id}"></div>

<script>
(function () {{
  const plots = {json.dumps(encoded_plots)};
  const select = document.getElementById("{select_id}");
  const container = document.getElementById("{container_id}");

  function update(selected) {{
    const img = document.createElement('img');
    img.src = 'data:image/png;base64,' + plots[selected];
    img.style.maxWidth = '100%';
    img.style.border = '1px solid #ddd';
    container.replaceChildren(img);
  }}

  select.addEventListener('change', () => update(select.value));
  update(select.value);
}})();
</script>
'''


def render_parameter_grid_figure(
    values_by_parameter: dict[str, pd.Series],
    *,
    title_suffix: str = "pre-fire observations",
    xlabel: str = "Pre-fire observations",
    nrows: int = 5,
    ncols: int = 2,
    figsize: tuple[float, float] = (8, 14),
):
    """Static small-multiples grid: the PDF fallback for the HTML dropdown."""
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    for parameter, ax in zip(values_by_parameter, axes.flat):
        plot_single_pre_fire_obs_distribution(values_by_parameter[parameter], parameter, ax=ax)
        ax.set_title(f"{parameter} {title_suffix}")
        ax.set_xlabel(xlabel)
    fig.tight_layout()
    return fig