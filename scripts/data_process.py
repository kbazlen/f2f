"""DuckDB queries used by the Fire-to-Faucet Quarto report."""

import duckdb
import pandas as pd


WQ_PARAMETERS = [
    "chla",
    "cdom",
    "doc",
    "sdd",
    "tss",
    "toc",
    "turbidity",
    "ph",
    "spcond",
    "alkalinity",
]


def _run(query: str) -> pd.DataFrame:
    return duckdb.sql(query).df()


def _count(query: str, column: str) -> int:
    return int(_run(query)[column].iloc[0])


def _burn_fraction_column(scope: str) -> str:
    if scope == "catchment":
        return "burned_frac"
    if scope == "upstream":
        return "upstream_burned_frac"
    raise ValueError('scope must be "catchment" or "upstream"')


def _validate_parameter(parameter: str) -> str:
    if parameter not in WQ_PARAMETERS:
        raise ValueError(f"parameter must be one of: {', '.join(WQ_PARAMETERS)}")
    return f"n_obs_{parameter}"


def count_catchments_above_burn_threshold(
    fire_path: str, *, x: float = 0.5, scope: str = "catchment"
) -> int:
    """Count distinct catchments above a local or upstream burn threshold."""
    fraction = _burn_fraction_column(scope)
    return _count(
        f"""
        SELECT COUNT(DISTINCT comid) AS n_catchments
        FROM '{fire_path}'
        WHERE {fraction} > {x}
        """,
        "n_catchments",
    )


def count_catchments_with_site_above_burn_threshold(
    fire_path: str, site_nhd_path: str, *, x: float = 0.5
) -> int:
    """Count burned catchments containing at least one monitoring site."""
    return _count(
        f"""
        SELECT COUNT(DISTINCT cf.comid) AS n_catchments
        FROM '{fire_path}' cf
        JOIN '{site_nhd_path}' s
          ON cf.comid = TRY_CAST(s.fl_nhd_id AS BIGINT)
        WHERE cf.burned_frac > {x}
        """,
        "n_catchments",
    )


def count_sites_above_burn_threshold(
    fire_path: str,
    site_nhd_path: str | None = None,
    *,
    x: float = 0.5,
    scope: str = "catchment",
) -> int:
    """Count distinct sites above a local or upstream burn threshold."""
    if scope == "catchment":
        if site_nhd_path is None:
            raise ValueError('site_nhd_path is required for scope="catchment"')
        query = f"""
            SELECT COUNT(DISTINCT s.MonitoringLocationIdentifier) AS n_sites
            FROM '{fire_path}' cf
            JOIN '{site_nhd_path}' s
              ON cf.comid = TRY_CAST(s.fl_nhd_id AS BIGINT)
            WHERE cf.burned_frac > {x}
        """
    elif scope == "upstream":
        query = f"""
            SELECT COUNT(DISTINCT MonitoringLocationIdentifier) AS n_sites
            FROM '{fire_path}'
            WHERE upstream_burned_frac > {x}
        """
    else:
        raise ValueError('scope must be "catchment" or "upstream"')
    return _count(query, "n_sites")


def count_catchments_above_high_severity_threshold(
    severity_path: str,
    fire_path: str | None = None,
    *,
    x: float = 0.5,
    scope: str = "catchment",
) -> int:
    """Count catchments above a local or upstream high-severity threshold."""
    if scope == "catchment":
        if fire_path is None:
            raise ValueError('fire_path is required for scope="catchment"')
        query = f"""
            SELECT COUNT(DISTINCT cf.comid) AS n_catchments
            FROM '{fire_path}' cf
            JOIN '{severity_path}' cs
              ON cf.comid = cs.comid AND cf.ig_year = cs.year
            WHERE cs.sev4_sqkm / cf.catch_sqkm > {x}
        """
    elif scope == "upstream":
        query = f"""
            SELECT COUNT(DISTINCT comid) AS n_catchments
            FROM '{severity_path}'
            WHERE upstream_sev4_sqkm / upstream_area_sqkm > {x}
        """
    else:
        raise ValueError('scope must be "catchment" or "upstream"')
    return _count(query, "n_catchments")


def count_catchments_with_site_above_high_severity_threshold(
    severity_path: str,
    site_nhd_path: str,
    fire_path: str,
    *,
    x: float = 0.5,
) -> int:
    """Count high-severity-burned catchments containing a monitoring site."""
    return _count(
        f"""
        SELECT COUNT(DISTINCT cf.comid) AS n_catchments
        FROM '{fire_path}' cf
        JOIN '{severity_path}' cs
          ON cf.comid = cs.comid AND cf.ig_year = cs.year
        JOIN '{site_nhd_path}' s
          ON cf.comid = TRY_CAST(s.fl_nhd_id AS BIGINT)
        WHERE cs.sev4_sqkm / cf.catch_sqkm > {x}
        """,
        "n_catchments",
    )


def count_sites_above_high_severity_threshold(
    severity_path: str,
    site_nhd_path: str | None = None,
    fire_path: str | None = None,
    *,
    x: float = 0.5,
    scope: str = "catchment",
) -> int:
    """Count distinct sites above a local or upstream high-severity threshold."""
    if fire_path is None:
        raise ValueError("fire_path is required")
    if scope == "catchment":
        if site_nhd_path is None:
            raise ValueError('site_nhd_path is required for scope="catchment"')
        query = f"""
            SELECT COUNT(DISTINCT s.MonitoringLocationIdentifier) AS n_sites
            FROM '{fire_path}' cf
            JOIN '{severity_path}' cs
              ON cf.comid = cs.comid AND cf.ig_year = cs.year
            JOIN '{site_nhd_path}' s
              ON cf.comid = TRY_CAST(s.fl_nhd_id AS BIGINT)
            WHERE cs.sev4_sqkm / cf.catch_sqkm > {x}
        """
    elif scope == "upstream":
        query = f"""
            SELECT COUNT(DISTINCT sf.MonitoringLocationIdentifier) AS n_sites
            FROM '{severity_path}' cs
            JOIN '{fire_path}' sf
              ON cs.comid = sf.comid AND cs.year = sf.year
            WHERE cs.upstream_sev4_sqkm / cs.upstream_area_sqkm > {x}
        """
    else:
        raise ValueError('scope must be "catchment" or "upstream"')
    return _count(query, "n_sites")


def get_fires_above_burn_threshold(
    fire_path: str,
    site_nhd_path: str,
    *,
    x: float = 0.5,
    scope: str = "catchment",
) -> pd.DataFrame:
    """Return qualifying fire locations for mapping."""
    if scope == "catchment":
        query = f"""
                        SELECT cf.comid, MAX(cf.burned_frac) AS burned_frac,
                   AVG(s.lat) AS lat, AVG(s.lon) AS lon
            FROM '{fire_path}' cf
            JOIN '{site_nhd_path}' s
              ON cf.comid = TRY_CAST(s.fl_nhd_id AS BIGINT)
            WHERE cf.burned_frac > {x}
                        GROUP BY cf.comid
        """
    elif scope == "upstream":
        query = f"""
            SELECT sf.comid, sf.year, sf.upstream_burned_frac,
                   AVG(s.lat) AS lat, AVG(s.lon) AS lon
            FROM '{fire_path}' sf
            JOIN '{site_nhd_path}' s USING (MonitoringLocationIdentifier)
            WHERE sf.upstream_burned_frac > {x}
            GROUP BY sf.comid, sf.year, sf.upstream_burned_frac
        """
    else:
        raise ValueError('scope must be "catchment" or "upstream"')
    return _run(query)


def get_fires_above_high_severity_threshold(
    severity_path: str,
    site_nhd_path: str,
    fire_path: str | None = None,
    *,
    x: float = 0.5,
    scope: str = "catchment",
) -> pd.DataFrame:
    """Return qualifying high-severity fire locations for mapping."""
    if fire_path is None:
        raise ValueError("fire_path is required")
    if scope == "catchment":
        query = f"""
                 SELECT cf.comid,
                     MAX(cs.sev4_sqkm / cf.catch_sqkm) AS high_sev_frac,
                   AVG(s.lat) AS lat, AVG(s.lon) AS lon
            FROM '{fire_path}' cf
            JOIN '{severity_path}' cs
              ON cf.comid = cs.comid AND cf.ig_year = cs.year
            JOIN '{site_nhd_path}' s
              ON cf.comid = TRY_CAST(s.fl_nhd_id AS BIGINT)
            WHERE cs.sev4_sqkm / cf.catch_sqkm > {x}
                        GROUP BY cf.comid
        """
    elif scope == "upstream":
        query = f"""
            SELECT cs.comid, cs.year,
                   cs.upstream_sev4_sqkm / cs.upstream_area_sqkm AS high_sev_frac,
                   AVG(s.lat) AS lat, AVG(s.lon) AS lon
            FROM '{severity_path}' cs
            JOIN '{fire_path}' sf
              ON cs.comid = sf.comid AND cs.year = sf.year
            JOIN '{site_nhd_path}' s USING (MonitoringLocationIdentifier)
            WHERE cs.upstream_sev4_sqkm / cs.upstream_area_sqkm > {x}
            GROUP BY cs.comid, cs.year,
                     cs.upstream_sev4_sqkm / cs.upstream_area_sqkm
        """
    else:
        raise ValueError('scope must be "catchment" or "upstream"')
    return _run(query)


def count_fire_events_above_burn_threshold(
    fire_path: str, site_nhd_path: str, *, x: float = 0.5
) -> int:
    """Count qualifying (site, fire event) pairs above a burn threshold.

    Unlike `count_sites_above_burn_threshold`, a site is counted once per
    distinct qualifying fire event rather than once overall.
    """
    return _count(
        f"""
        SELECT COUNT(*) AS n_events
        FROM (
            SELECT DISTINCT s.MonitoringLocationIdentifier AS site, cf.event_id AS event_id
            FROM '{fire_path}' cf
            JOIN '{site_nhd_path}' s
              ON cf.comid = TRY_CAST(s.fl_nhd_id AS BIGINT)
            WHERE cf.burned_frac > {x}
        )
        """,
        "n_events",
    )


def count_fire_events_with_quarterly_wq_above_burn_threshold(
    catchment_fire_path: str,
    site_nhd_path: str,
    panel_path: str,
    parameter: str,
    *,
    x: float = 0.5,
    n_years: int = 3,
    min_obs: int = 4,
) -> int:
    """Count qualifying fire events meeting annual observation minimums before and after.

    A fire event is one (site, fire) pair; a site with multiple qualifying
    fires that each independently meet the coverage bar is counted once per
    fire, not once overall.
    """
    n_obs = _validate_parameter(parameter)
    return _count(
        f"""
        WITH eligible_fires AS (
            SELECT DISTINCT s.MonitoringLocationIdentifier AS site,
                            cf.event_id AS event_id,
                            cf.ig_year AS fire_year
            FROM '{catchment_fire_path}' cf
            JOIN '{site_nhd_path}' s
              ON cf.comid = TRY_CAST(s.fl_nhd_id AS BIGINT)
            WHERE cf.burned_frac > {x}
        )
        SELECT COUNT(*) AS n_events
        FROM eligible_fires ef
        WHERE (
            SELECT COUNT(*)
            FROM '{panel_path}' p
            WHERE p.site = ef.site
              AND p.yr BETWEEN ef.fire_year - {n_years} AND ef.fire_year - 1
              AND p.{n_obs} >= {min_obs}
        ) = {n_years}
          AND (
            SELECT COUNT(*)
            FROM '{panel_path}' p
            WHERE p.site = ef.site
              AND p.yr BETWEEN ef.fire_year + 1 AND ef.fire_year + {n_years}
              AND p.{n_obs} >= {min_obs}
        ) = {n_years}
        """,
        "n_events",
    )


def build_wq_availability_table(
    catchment_fire_path: str,
    site_nhd_path: str,
    panel_path: str,
    thresholds_pct: list[int],
    parameters: list[str] = WQ_PARAMETERS,
    *,
    n_years: int = 3,
    min_obs: int = 4,
) -> pd.DataFrame:
    """Build qualifying fire-event counts by burn threshold and parameter.

    Includes an `n_events` column: the total number of qualifying (site,
    fire) pairs at that threshold, for use as a percentage denominator.
    """
    rows = []
    for threshold in thresholds_pct:
        row = {
            "threshold_pct": threshold,
            "n_events": count_fire_events_above_burn_threshold(
                catchment_fire_path, site_nhd_path, x=threshold / 100
            ),
        }
        row.update(
            {
                parameter: count_fire_events_with_quarterly_wq_above_burn_threshold(
                    catchment_fire_path,
                    site_nhd_path,
                    panel_path,
                    parameter,
                    x=threshold / 100,
                    n_years=n_years,
                    min_obs=min_obs,
                )
                for parameter in parameters
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def count_matchups_above_burn_threshold(
    catchment_fire_path: str,
    site_nhd_path: str,
    panel_path: str,
    parameter: str,
    *,
    x: float = 0.5,
) -> int:
    """Count matchup rows at sites in catchments above a burn threshold.

    Summed from the panel's `n_match_<parameter>` columns across all years,
    the same site-year table used by the availability tables.
    """
    _validate_parameter(parameter)
    n_match = f"n_match_{parameter}"
    return _count(
        f"""
        WITH eligible_sites AS (
            SELECT DISTINCT s.MonitoringLocationIdentifier AS site
            FROM '{catchment_fire_path}' cf
            JOIN '{site_nhd_path}' s
              ON cf.comid = TRY_CAST(s.fl_nhd_id AS BIGINT)
            WHERE cf.burned_frac > {x}
        )
        SELECT COALESCE(SUM(p.{n_match}), 0) AS n_matchups
        FROM '{panel_path}' p
        JOIN eligible_sites e
          ON p.site = e.site
        """,
        "n_matchups",
    )


def build_matchup_count_table(
    catchment_fire_path: str,
    site_nhd_path: str,
    panel_path: str,
    thresholds_pct: list[int],
    parameters: list[str] = WQ_PARAMETERS,
) -> pd.DataFrame:
    """Build matchup-row counts by burn threshold and parameter."""
    rows = []
    for threshold in thresholds_pct:
        row = {"threshold_pct": threshold}
        row.update(
            {
                parameter: count_matchups_above_burn_threshold(
                    catchment_fire_path,
                    site_nhd_path,
                    panel_path,
                    parameter,
                    x=threshold / 100,
                )
                for parameter in parameters
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def count_fire_events_with_quarterly_matchups_above_burn_threshold(
    catchment_fire_path: str,
    site_nhd_path: str,
    panel_path: str,
    parameter: str,
    *,
    x: float = 0.5,
    n_years: int = 3,
    min_matchups: int = 4,
) -> int:
    """Count qualifying fire events with annual matchup minimums before and after.

    A fire event is one (site, fire) pair; a site with multiple qualifying
    fires that each independently meet the coverage bar is counted once per
    fire, not once overall. Matchup counts come from the panel's
    `n_match_<parameter>` columns, the same site-year table used for the
    in-situ `n_obs_<parameter>` counts, so both availability tables are
    computed the same way.
    """
    _validate_parameter(parameter)
    n_match = f"n_match_{parameter}"
    return _count(
        f"""
        WITH eligible_fires AS (
            SELECT DISTINCT s.MonitoringLocationIdentifier AS site,
                            cf.event_id AS event_id,
                            cf.ig_year AS fire_year
            FROM '{catchment_fire_path}' cf
            JOIN '{site_nhd_path}' s
              ON cf.comid = TRY_CAST(s.fl_nhd_id AS BIGINT)
            WHERE cf.burned_frac > {x}
        )
        SELECT COUNT(*) AS n_events
        FROM eligible_fires ef
        WHERE (
            SELECT COUNT(*)
            FROM '{panel_path}' p
            WHERE p.site = ef.site
              AND p.yr BETWEEN ef.fire_year - {n_years} AND ef.fire_year - 1
              AND p.{n_match} >= {min_matchups}
        ) = {n_years}
          AND (
            SELECT COUNT(*)
            FROM '{panel_path}' p
            WHERE p.site = ef.site
              AND p.yr BETWEEN ef.fire_year + 1 AND ef.fire_year + {n_years}
              AND p.{n_match} >= {min_matchups}
        ) = {n_years}
        """,
        "n_events",
    )


def build_matchup_availability_table(
    catchment_fire_path: str,
    site_nhd_path: str,
    panel_path: str,
    thresholds_pct: list[int],
    parameters: list[str] = WQ_PARAMETERS,
    *,
    n_years: int = 3,
    min_matchups: int = 4,
) -> pd.DataFrame:
    """Build qualifying fire-event counts meeting annual matchup minimums by burn threshold."""
    rows = []
    for threshold in thresholds_pct:
        row = {"threshold_pct": threshold}
        row.update(
            {
                parameter: count_fire_events_with_quarterly_matchups_above_burn_threshold(
                    catchment_fire_path,
                    site_nhd_path,
                    panel_path,
                    parameter,
                    x=threshold / 100,
                    n_years=n_years,
                    min_matchups=min_matchups,
                )
                for parameter in parameters
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def get_sites_with_dual_coverage(
    catchment_fire_path: str,
    site_nhd_path: str,
    panel_path: str,
    parameters: list[str] = WQ_PARAMETERS,
    *,
    x: float = 0.2,
    n_years: int = 3,
    min_obs: int = 4,
    min_matchups: int = 4,
) -> pd.DataFrame:
    """Sites with both quarterly in-situ and quarterly matchup coverage.

    Returns one row per site (deduplicated across parameters) in a catchment
    burned more than `x`, where at least one parameter has >=`min_obs`
    in-situ observations per year AND >=`min_matchups` Landsat matchup rows
    per year, in each of the `n_years` years before and after the fire.
    Both counts come from the panel's `n_obs_<parameter>` and
    `n_match_<parameter>` columns.
    """
    frames = []
    for parameter in parameters:
        n_obs_col = _validate_parameter(parameter)
        n_match_col = f"n_match_{parameter}"
        df = _run(
            f"""
            WITH eligible_fires AS (
                SELECT DISTINCT s.MonitoringLocationIdentifier AS site,
                                cf.ig_year AS fire_year,
                                s.lat, s.lon
                FROM '{catchment_fire_path}' cf
                JOIN '{site_nhd_path}' s
                  ON cf.comid = TRY_CAST(s.fl_nhd_id AS BIGINT)
                WHERE cf.burned_frac > {x}
            )
            SELECT DISTINCT ef.site, ef.lat, ef.lon
            FROM eligible_fires ef
            WHERE (
                SELECT COUNT(*) FROM '{panel_path}' p
                WHERE p.site = ef.site
                  AND p.yr BETWEEN ef.fire_year - {n_years} AND ef.fire_year - 1
                  AND p.{n_obs_col} >= {min_obs}
            ) = {n_years}
              AND (
                SELECT COUNT(*) FROM '{panel_path}' p
                WHERE p.site = ef.site
                  AND p.yr BETWEEN ef.fire_year + 1 AND ef.fire_year + {n_years}
                  AND p.{n_obs_col} >= {min_obs}
            ) = {n_years}
              AND (
                SELECT COUNT(*) FROM '{panel_path}' p
                WHERE p.site = ef.site
                  AND p.yr BETWEEN ef.fire_year - {n_years} AND ef.fire_year - 1
                  AND p.{n_match_col} >= {min_matchups}
            ) = {n_years}
              AND (
                SELECT COUNT(*) FROM '{panel_path}' p
                WHERE p.site = ef.site
                  AND p.yr BETWEEN ef.fire_year + 1 AND ef.fire_year + {n_years}
                  AND p.{n_match_col} >= {min_matchups}
            ) = {n_years}
            """
        )
        frames.append(df)
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["site", "lat", "lon"])
    return combined.drop_duplicates(subset="site").reset_index(drop=True)


def get_pre_fire_obs_counts(
    catchment_fire_path: str,
    site_nhd_path: str,
    panel_path: str,
    parameter: str,
    *,
    x: float = 0.5,
    n_years: int = 3,
) -> pd.DataFrame:
    """Return pre-fire observation totals for each qualifying site-fire event."""
    n_obs = _validate_parameter(parameter)
    return _run(
        f"""
        WITH eligible_fires AS (
            SELECT DISTINCT s.MonitoringLocationIdentifier AS site,
                            cf.ig_year AS fire_year
            FROM '{catchment_fire_path}' cf
            JOIN '{site_nhd_path}' s
              ON cf.comid = TRY_CAST(s.fl_nhd_id AS BIGINT)
            WHERE cf.burned_frac > {x}
        )
        SELECT ef.site, ef.fire_year,
               COALESCE(SUM(p.{n_obs}), 0) AS pre_fire_obs
        FROM eligible_fires ef
        LEFT JOIN '{panel_path}' p
          ON p.site = ef.site
         AND p.yr BETWEEN ef.fire_year - {n_years} AND ef.fire_year - 1
        GROUP BY ef.site, ef.fire_year
        """
    )


def get_pre_fire_matchup_counts(
    catchment_fire_path: str,
    site_nhd_path: str,
    panel_path: str,
    parameter: str,
    *,
    x: float = 0.5,
    n_years: int = 3,
) -> pd.DataFrame:
    """Return pre-fire matchup totals for each qualifying site-fire event.

    Matchup counts come from the panel's `n_match_<parameter>` columns, the
    same site-year table used by `get_pre_fire_obs_counts`.
    """
    _validate_parameter(parameter)
    n_match = f"n_match_{parameter}"
    return _run(
        f"""
        WITH eligible_fires AS (
            SELECT DISTINCT s.MonitoringLocationIdentifier AS site,
                            cf.ig_year AS fire_year
            FROM '{catchment_fire_path}' cf
            JOIN '{site_nhd_path}' s
              ON cf.comid = TRY_CAST(s.fl_nhd_id AS BIGINT)
            WHERE cf.burned_frac > {x}
        )
        SELECT ef.site, ef.fire_year,
               COALESCE(SUM(p.{n_match}), 0) AS pre_fire_matchups
        FROM eligible_fires ef
        LEFT JOIN '{panel_path}' p
          ON p.site = ef.site
         AND p.yr BETWEEN ef.fire_year - {n_years} AND ef.fire_year - 1
        GROUP BY ef.site, ef.fire_year
        """
    )


def get_best_site_fire_event(
    catchment_fire_path: str,
    site_nhd_path: str,
    water_quality_path: str,
    matchup_path: str,
    *,
    x: float = 0.2,
    n_years: int = 3,
    min_matchups_per_year: int | None = None,
) -> pd.Series:
    """Select the qualifying site-fire event with the most observations."""
    coverage_filter = ""
    coverage_cte = ""
    if min_matchups_per_year is not None:
        coverage_cte = f"""
        , annual_matchups AS (
            SELECT ef.site, ef.comid, ef.event_id, ef.fire_year,
                   EXTRACT(YEAR FROM m.harmonized_utc) AS matchup_year,
                   COUNT(*) AS n_matchups
            FROM eligible_fires ef
            JOIN '{matchup_path}' m
              ON m.MonitoringLocationIdentifier = ef.site
             AND EXTRACT(YEAR FROM m.harmonized_utc)
                 BETWEEN ef.fire_year - {n_years} AND ef.fire_year + {n_years}
            GROUP BY ef.site, ef.comid, ef.event_id, ef.fire_year,
                     EXTRACT(YEAR FROM m.harmonized_utc)
        )
        """
        coverage_filter = f"""
        AND (
            SELECT COUNT(*)
            FROM annual_matchups am
            WHERE am.site = ef.site
              AND am.comid = ef.comid
              AND am.event_id = ef.event_id
              AND am.fire_year = ef.fire_year
              AND am.matchup_year BETWEEN ef.fire_year - {n_years}
                                      AND ef.fire_year - 1
              AND am.n_matchups >= {min_matchups_per_year}
        ) = {n_years}
        AND (
            SELECT COUNT(*)
            FROM annual_matchups am
            WHERE am.site = ef.site
              AND am.comid = ef.comid
              AND am.event_id = ef.event_id
              AND am.fire_year = ef.fire_year
              AND am.matchup_year BETWEEN ef.fire_year + 1
                                      AND ef.fire_year + {n_years}
              AND am.n_matchups >= {min_matchups_per_year}
        ) = {n_years}
        """
    result = _run(
        f"""
        WITH eligible_fires AS (
            SELECT DISTINCT s.MonitoringLocationIdentifier AS site,
                            cf.comid,
                            cf.event_id,
                            cf.incid_name AS fire_name,
                            cf.ig_year AS fire_year,
                            TRY_CAST(cf.ig_date AS DATE) AS fire_date,
                            s.lat,
                            s.lon
            FROM '{catchment_fire_path}' cf
            JOIN '{site_nhd_path}' s
              ON cf.comid = TRY_CAST(s.fl_nhd_id AS BIGINT)
            WHERE cf.burned_frac > {x}
        ), observation_counts AS (
            SELECT ef.site, ef.comid, ef.event_id, ef.fire_year,
                   COUNT(*) AS n_observations
            FROM eligible_fires ef
            JOIN '{water_quality_path}' w
              ON w.MonitoringLocationIdentifier = ef.site
             AND EXTRACT(YEAR FROM w.harmonized_utc)
                 BETWEEN ef.fire_year - {n_years} AND ef.fire_year + {n_years}
            GROUP BY ef.site, ef.comid, ef.event_id, ef.fire_year
        ){coverage_cte}, matchup_counts AS (
             SELECT ef.site, ef.comid, ef.event_id, ef.fire_year,
                 COUNT(*) AS n_matchups
             FROM eligible_fires ef
             JOIN '{matchup_path}' m
            ON m.MonitoringLocationIdentifier = ef.site
              AND EXTRACT(YEAR FROM m.harmonized_utc)
               BETWEEN ef.fire_year - {n_years} AND ef.fire_year + {n_years}
             GROUP BY ef.site, ef.comid, ef.event_id, ef.fire_year
         )
         SELECT ef.*, COALESCE(oc.n_observations, 0) AS n_observations,
             COALESCE(mc.n_matchups, 0) AS n_matchups
        FROM eligible_fires ef
        LEFT JOIN observation_counts oc
          ON oc.site = ef.site
         AND oc.comid = ef.comid
         AND oc.event_id = ef.event_id
         AND oc.fire_year = ef.fire_year
                LEFT JOIN matchup_counts mc
                    ON mc.site = ef.site
                 AND mc.comid = ef.comid
                 AND mc.event_id = ef.event_id
                 AND mc.fire_year = ef.fire_year
                WHERE COALESCE(mc.n_matchups, 0) > 0
                {coverage_filter}
                ORDER BY n_observations DESC, ef.fire_year DESC, ef.site
        LIMIT 1
        """
    )
    if result.empty:
        raise ValueError("No qualifying site-fire event was found")
    return result.iloc[0]

