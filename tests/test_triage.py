"""Tests for Layer 4 — the rule-based Triage Agent (pure logic, no dataset)."""
import pandas as pd
import pytest

from pipeline.triage import (
    ACTION_BY_SEVERITY,
    RULES,
    add_rul_slope,
    severity_for,
    summarise,
    triage,
    work_orders_for,
)


def test_critical_on_short_rul():
    sev, reason = severity_for(predicted_rul=10, anomaly=0.2, rul_slope=-1.0)
    assert sev == "CRITICAL"
    assert "RUL 10c" in reason


def test_critical_on_extreme_anomaly_even_with_long_rul():
    sev, reason = severity_for(predicted_rul=120, anomaly=0.9995, rul_slope=0.0)
    assert sev == "CRITICAL"
    assert "anomaly" in reason


def test_high_band_boundary_is_inclusive():
    assert severity_for(RULES["HIGH"][0], 0.1, 0.0)[0] == "HIGH"          # exactly 30c
    assert severity_for(RULES["HIGH"][0] + 0.5, 0.1, 0.0)[0] == "MEDIUM"  # just above


def test_accelerating_degradation_plus_anomaly_is_high():
    sev, reason = severity_for(predicted_rul=50, anomaly=0.998, rul_slope=-2.0)
    assert sev == "HIGH"
    assert "accelerating" in reason


def test_watch_band_anomaly_without_urgency_is_medium_not_high():
    # anomaly clears the 0.95 watch band but not the 0.997 high band, and life
    # is burning normally → this machine waits in the human queue, it is not an
    # auto-work-order emergency
    sev, reason = severity_for(predicted_rul=70, anomaly=0.96, rul_slope=-1.0)
    assert sev == "MEDIUM"
    assert "anomaly" in reason


def test_medium_on_watchlist_rul():
    sev, reason = severity_for(predicted_rul=45, anomaly=0.05, rul_slope=-1.0)
    assert sev == "MEDIUM"
    assert "RUL 45c" in reason


def test_low_when_all_signals_calm():
    sev, reason = severity_for(predicted_rul=90, anomaly=0.1, rul_slope=-1.0)
    assert sev == "LOW"
    assert "RUL 90c" in reason


def test_every_rule_states_its_threshold():
    for rul, anom, slope in [(10, 0.2, -1), (120, 0.9, 0), (25, 0.1, -1),
                             (50, 0.65, -2), (45, 0.05, -1), (90, 0.1, -1)]:
        _sev, reason = severity_for(rul, anom, slope)
        assert str(int(rul)) in reason or "anomaly" in reason


def test_add_rul_slope_measures_life_burn_rate():
    rows = pd.DataFrame(
        {
            "unit_id": [1] * 6,
            "cycle": [1, 2, 3, 4, 5, 6],
            "predicted_rul": [50, 48, 46, 44, 42, 40],  # losing 2c per cycle
        }
    )
    out = add_rul_slope(rows, window=3)
    assert out["rul_slope"].iloc[-1] == pytest.approx(-2.0)
    assert out["rul_slope"].iloc[0] == 0.0  # no history yet


def test_triage_reads_trend_from_full_history():
    full = pd.DataFrame(
        {
            "unit_id": [1] * 7,
            "cycle": [1, 2, 3, 4, 5, 6, 7],
            "predicted_rul": [80, 78, 76, 74, 72, 70, 68],
            "anomaly": [0.998] * 7,
        }
    )
    current = full.tail(1)[["unit_id", "cycle", "predicted_rul", "anomaly"]]
    decisions = triage(current, full_rows=full, window=3)
    assert len(decisions) == 1
    d = decisions[0]
    assert d.rul_slope == pytest.approx(-2.0)
    # anomaly ≥ 0.997 + accelerating burn → HIGH even though RUL 68 is comfortable
    assert d.severity == "HIGH"
    assert d.action == "AUTO_WORK_ORDER"


def test_work_orders_skip_low_and_set_status():
    full = pd.DataFrame(
        {
            "unit_id": [1, 1, 2, 2, 3, 3],
            "cycle": [1, 2, 1, 2, 1, 2],
            "predicted_rul": [10, 8, 45, 44, 120, 118],
            "anomaly": [0.2, 0.2, 0.1, 0.1, 0.1, 0.1],
        }
    )
    current = full.sort_values("cycle").groupby("unit_id", as_index=False).tail(1)
    decisions = triage(current, full_rows=full, window=2)
    orders = work_orders_for(decisions, subset="FD001")

    by_engine = {o["engine_id"]: o for o in orders}
    assert set(by_engine) == {1, 2}          # engine 3 (LOW) never becomes a work order
    assert by_engine[1]["status"] == "OPEN"  # critical orders itself
    assert by_engine[2]["status"] == "HUMAN_REVIEW"  # medium waits for a human
    assert all(o["subset"] == "FD001" for o in orders)


def test_action_mapping_covers_all_severities():
    for severity, (action, status) in ACTION_BY_SEVERITY.items():
        assert severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
        assert action in ("AUTO_WORK_ORDER", "HUMAN_REVIEW", "LOG_ONLY")
        assert status in ("OPEN", "HUMAN_REVIEW", "NO_WORK_ORDER")


def test_summarise_counts_every_severity():
    assert summarise([]) == {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
