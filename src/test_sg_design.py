"""Behavioural checks for sg_design.py (Q2). Run: python3 -m pytest code/ -q

The march tests take a while because every property call goes through IAPWS-IF97.
"""
import pytest

import sg_design as sg

SPEC_GIVEN = dict(sg.SPEC_GIVEN)                    # 100 bar as specified (infeasible)
SPEC = dict(sg.SPEC_GIVEN, P_steam_bar=70.0)        # the feasible design pressure


# ------------------------------------------------------------------ energy balance / pinch
def test_duty_per_steam_generator():
    eb = sg.energy_balance(SPEC)
    assert eb["Q_sg"] == pytest.approx(781.25e6, rel=1e-9)
    assert 4000 < eb["m_pri"] < 4800
    assert eb["m_sec"] * (eb["h_sec_out"] - eb["h_fw"]) == pytest.approx(eb["Q_sg"], rel=1e-9)


def test_spec_as_given_has_a_temperature_cross():
    pa = sg.pinch_analysis(SPEC_GIVEN)
    assert pa["dT_min"] < 0


def test_70_bar_design_has_a_positive_pinch():
    pa = sg.pinch_analysis(SPEC)
    assert 8.0 < pa["dT_boil"] < 14.0
    assert pa["dT_min"] == pytest.approx(5.0, abs=0.2)       # the terminal approach at the hot end


def test_max_feasible_pressure_for_10K_pinch():
    P = sg.max_feasible_steam_pressure(SPEC_GIVEN, dT_pinch_min=10.0)
    assert 66.0 < P < 76.0


# ------------------------------------------------------------------ mechanical sizing
def test_asme_tube_thickness_and_gauge_rounding():
    t = sg.asme_tube_thickness(d_o=15.875e-3, P=19.8e6, S=115e6)
    assert t == pytest.approx(1.28e-3, abs=0.03e-3)
    assert sg.round_up_bwg(t) == pytest.approx(1.473e-3, abs=1e-6)   # BWG 17


def test_asme_shell_thickness():
    t = sg.asme_shell_thickness(D_i=2.5, P=7.7e6, S=115e6)
    assert t == pytest.approx(0.0872, abs=0.001)


# ------------------------------------------------------------------ correlations
def test_dittus_boelter_value():
    assert sg.nu_dittus_boelter(1e5, 1.0, 0.4) == pytest.approx(230.0, rel=1e-6)


def test_filonenko_friction_matches_blasius_at_1e5():
    assert sg.friction_factor(1e5) == pytest.approx(0.0178, abs=0.001)


def test_chen_reduces_to_single_phase_when_F_and_S_are_trivial():
    sat = sg.saturation(70.0)
    # 1/Xtt <= 0.1 -> F = 1; the convective term then equals the liquid Dittus-Boelter value
    h = sg.chen(G=200.0, x=1e-4, D=0.0184, sat=sat, dT_wall=0.0)
    assert h["F"] == pytest.approx(1.0)
    assert h["h_conv"] == pytest.approx(h["h_l"], rel=1e-9)
    assert h["h_nb"] == 0.0                      # no wall superheat -> no nucleate term


def test_chen_magnitude_in_the_boiling_region():
    sat = sg.saturation(70.0)
    h = sg.chen(G=200.0, x=0.3, D=0.0184, sat=sat, dT_wall=5.0)
    assert 5e3 < h["h"] < 6e4
    assert h["F"] > 1.0 and 0.0 < h["S"] < 1.0


def test_dougall_rohsenow_increases_with_quality():
    sat = sg.saturation(70.0)
    h1 = sg.dougall_rohsenow(G=200.0, x=0.9, D=0.0184, sat=sat)
    h2 = sg.dougall_rohsenow(G=200.0, x=0.99, D=0.0184, sat=sat)
    assert 500 < h1 < h2 < 5000


# ------------------------------------------------------------------ the march
@pytest.fixture(scope="module")
def design():
    return sg.design(SPEC, sg.DESIGN)


def test_march_closes_the_energy_balance(design):
    rep = design["report"]
    assert rep["T_pri_top"] == pytest.approx(SPEC["T_pri_in"], abs=0.05)
    assert rep["T_sec_top"] == pytest.approx(SPEC["T_steam_out"], abs=0.05)
    assert rep["P_sec_out"] == pytest.approx(SPEC["P_steam_bar"], abs=0.01)
    seg = design["segments"]
    assert seg["T_sec"][-1] < SPEC["T_steam_out"] < seg["T_sec"][-1] + 2.0   # last segment inlet just below the outlet


def test_quality_and_enthalpy_increase_monotonically(design):
    seg = design["segments"]
    assert all(b >= a for a, b in zip(seg["x"][:-1], seg["x"][1:]))
    assert all(b > a for a, b in zip(seg["h_sec"][:-1], seg["h_sec"][1:]))
    assert sum(seg["dQ"]) == pytest.approx(design["eb"]["Q_sg"], rel=1e-6)


def test_march_uses_at_least_20_segments_and_regimes_in_order(design):
    seg = design["segments"]
    assert len(seg["z"]) >= 20
    order = []
    for r in seg["regime"]:
        if not order or order[-1] != r:
            order.append(r)
    assert order == ["subcooled", "nucleate boiling", "post-dryout", "superheated"]


def test_wall_temperature_lies_between_the_fluids(design):
    seg = design["segments"]
    for Tp, Ts, Two, Twi in zip(seg["T_pri"], seg["T_sec"], seg["T_wall_out"], seg["T_wall_in"]):
        assert Ts < Two <= Twi < Tp


def test_outputs_have_plausible_magnitudes(design):
    assert 5000 < design["N_tubes"] < 20000
    assert 8.0 < design["L_tube"] < 40.0
    assert 1.5 < design["D_shell"] < 4.5
    assert 0.04 < design["t_shell"] < 0.15
    assert 0.2e5 < design["dP_shell"] < 10e5
    assert 0.5e5 < design["dP_tube"] < 10e5
    assert 100e3 < design["weight"] < 2000e3


def test_segment_count_convergence(design):
    L20 = sg.design(SPEC, dict(sg.DESIGN, n_segments=20))["L_tube"]
    assert L20 == pytest.approx(design["L_tube"], rel=0.01)
    assert design["L_tube"] == pytest.approx(design["L_fine"], rel=0.005)
