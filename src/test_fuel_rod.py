"""Behavioural checks for fuel_rod.py (Q1). Run: python3 -m pytest code/ -q"""
import pytest

import fuel_rod as fr


def test_hydraulic_diameter_of_triangular_subchannel():
    # d [(2 sqrt3 / pi)(p/d)^2 - 1] for p = 12.5 mm, d = 10 mm
    assert fr.hydraulic_diameter_triangular(12.5e-3, 10e-3) == pytest.approx(7.229e-3, abs=2e-6)


def test_uo2_conductivity_fink_matches_literature_points():
    assert fr.k_uo2(1000.0) == pytest.approx(3.45, abs=0.15)      # W/m K at 1000 K
    assert fr.k_uo2(2000.0) == pytest.approx(2.06, abs=0.15)      # W/m K at 2000 K


def test_uo2_conductivity_integral_to_melting_is_about_93_W_per_cm():
    integral = fr.k_uo2_integral(273.15, 2840.0 + 273.15)        # W/m
    assert integral == pytest.approx(9300.0, rel=0.07)


def test_zircaloy_conductivity_matpro():
    assert fr.k_zircaloy(600.0) == pytest.approx(16.5, abs=0.6)


def test_water_properties_at_core_conditions():
    w = fr.water_props(T_C=310.0, P_bar=180.0)
    assert w["rho"] == pytest.approx(710.3, abs=1.0)
    assert w["Pr"] == pytest.approx(0.872, abs=0.01)


def test_weisman_reduces_to_dittus_boelter_where_bracket_is_one():
    pd = (1.0 + 0.2609) / 1.130      # bracket 1.130 pd - 0.2609 == 1
    assert fr.nu_weisman(1e5, 1.0, pd) == pytest.approx(fr.nu_dittus_boelter(1e5, 1.0), rel=1e-6)
    assert fr.nu_dittus_boelter(1e5, 1.0) == pytest.approx(230.0, rel=1e-6)


def test_fuel_limit_is_binding_and_self_consistent():
    r = fr.solve_fuel_rod()
    assert r["q_fuel"] < r["q_clad"]
    assert 40e3 < r["q_max"] < 90e3                 # W/m, plausible PWR range
    prof = fr.temperatures(r["q_max"], r)
    assert prof["T_centre"] == pytest.approx(2000.0, abs=0.5)
    assert prof["T_clad_in"] < 1200.0
    assert prof["T_clad_out"] > 310.0


def test_gap_resistance_lowers_the_limit():
    base = fr.solve_fuel_rod()["q_max"]
    gapped = fr.solve_fuel_rod(h_gap=5000.0)["q_max"]
    assert gapped < base


def test_fuel_limit_tolerates_coolant_temperature_change_weakly():
    base = fr.solve_fuel_rod()["q_max"]
    hot = fr.solve_fuel_rod(T_bulk=330.0)["q_max"]
    assert 0 < (base - hot) / base < 0.03
