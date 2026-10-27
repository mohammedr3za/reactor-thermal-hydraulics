# %% [markdown]
# ## Thermal-resistance chain
#
# Analytical thermal-resistance chain for a fuel rod on a triangular lattice. The code evaluates
# the closed-form expressions. Chain per metre of rod: coolant film, Zircaloy clad, (gap), UO₂ pellet.
#
# $$q'_{fuel} = \frac{T_{c,max} - T_b}{R_{film} + R_{clad} + R_{gap} + R_{fuel}}, \qquad
# q'_{clad} = \frac{T_{ci,max} - T_b}{R_{film} + R_{clad}}$$
#
# The smaller value is the permissible linear heat rate.

# %%
import math

import numpy as np
from iapws import IAPWS97

# ------------------------------------------------------------------ given data (SI)
ROD = dict(
    pitch=12.5e-3,          # m, triangular lattice
    d_clad_out=10.0e-3,     # m
    t_clad=0.5e-3,          # m, Zircaloy
    d_pellet=9.0e-3,        # m  (= clad ID, so no gap as set)
    L_active=3.0,           # m
    L_total=4.0,            # m
    T_bulk=310.0,           # °C, coolant
    P_bar=180.0,            # bar, coolant
    V=5.0,                  # m/s, interstitial velocity
    T_fuel_max=2000.0,      # °C, pellet centre limit
    T_clad_max=1200.0,      # °C, clad limit
)

# Plant data shared with Q2 (used only for the consistency check at the end)
PLANT = dict(P_e_MW=1000.0, eta=0.32, T_core_in=295.0, T_core_out=325.0)


# %% [markdown]
# ## Geometry of the interior sub-channel
#
# $$A = \frac{\sqrt{3}}{4}p^2 - \frac{\pi}{8}d^2, \qquad P_w = \frac{\pi d}{2}, \qquad
# D_e = \frac{4A}{P_w} = d\left[\frac{2\sqrt{3}}{\pi}\left(\frac{p}{d}\right)^2 - 1\right]$$
#
# The full unit cell of one rod has the flow area $\frac{\sqrt{3}}{2}p^2 - \frac{\pi}{4}d^2$.

# %%
def hydraulic_diameter_triangular(p, d):
    """Equivalent diameter of the interior sub-channel of a triangular rod lattice (m)."""
    return d * ((2.0 * math.sqrt(3.0) / math.pi) * (p / d) ** 2 - 1.0)


def flow_area_per_rod(p, d):
    """Coolant flow area of one unit cell (one rod) in a triangular lattice (m²)."""
    return (math.sqrt(3.0) / 2.0) * p ** 2 - (math.pi / 4.0) * d ** 2


# %% [markdown]
# ## Properties
#
# Water: IAPWS-IF97 at 310 °C and 180 bar. Zircaloy (MATPRO), $T$ in K:
#
# $$k_c = 7.51 + 2.09\times10^{-2}\,T - 1.45\times10^{-5}\,T^2 + 7.67\times10^{-9}\,T^3$$
#
# UO₂ at 95 % theoretical density (Fink 2000), $t = T/1000\ \mathrm{K}$:
#
# $$k_f = \frac{100}{7.5408 + 17.692\,t + 3.6142\,t^2} + \frac{6400}{t^{5/2}}\,e^{-16.35/t}$$
#
# The pellet uses the conductivity integral $\int_{T_s}^{T_c} k_f\,dT$.

# %%
def water_props(T_C, P_bar):
    w = IAPWS97(P=P_bar / 10.0, T=T_C + 273.15)
    return dict(rho=w.rho, mu=w.mu, k=w.k, cp=w.cp * 1e3, Pr=w.Prandt, h=w.h * 1e3,
                T_sat=IAPWS97(P=P_bar / 10.0, x=0.0).T - 273.15)


def k_zircaloy(T_K):
    """Zircaloy thermal conductivity, MATPRO (W/m K), T in K."""
    return 7.51 + 2.09e-2 * T_K - 1.45e-5 * T_K ** 2 + 7.67e-9 * T_K ** 3


def k_uo2(T_K):
    """UO2 thermal conductivity at 95 % theoretical density, Fink (2000) (W/m K), T in K."""
    t = np.asarray(T_K, dtype=float) / 1000.0
    return 100.0 / (7.5408 + 17.692 * t + 3.6142 * t ** 2) + 6400.0 / t ** 2.5 * np.exp(-16.35 / t)


def k_uo2_integral(T1_K, T2_K, n=2001):
    """∫ k_UO2 dT from T1 to T2 (W/m), trapezoidal on a fine grid."""
    T = np.linspace(T1_K, T2_K, n)
    return float(np.trapezoid(k_uo2(T), T))


def k_uo2_effective(T1_C, T2_C):
    """Mean conductivity over a temperature range, ∫k dT / ΔT (W/m K)."""
    return k_uo2_integral(T1_C + 273.15, T2_C + 273.15) / (T2_C - T1_C)


# %% [markdown]
# ## Film coefficient
#
# Weisman (1959) for triangular rod bundles, Todreas–Kazimi form, $1.1 \le p/d \le 1.5$:
#
# $$\mathrm{Nu} = 0.023\,\mathrm{Re}^{0.8}\,\mathrm{Pr}^{0.4}\left[1.130\,\frac{p}{d} - 0.2609\right], \qquad h = \frac{\mathrm{Nu}\,k}{D_e}$$
#
# Dittus–Boelter (bracket = 1) is the cross-check.

# %%
def nu_dittus_boelter(Re, Pr, n=0.4):
    return 0.023 * Re ** 0.8 * Pr ** n


def nu_weisman(Re, Pr, pd, n=0.4):
    return 0.023 * Re ** 0.8 * Pr ** n * (1.130 * pd - 0.2609)


def film_coefficient(rod, correlation="weisman"):
    w = water_props(rod["T_bulk"], rod["P_bar"])
    D_e = hydraulic_diameter_triangular(rod["pitch"], rod["d_clad_out"])
    Re = w["rho"] * rod["V"] * D_e / w["mu"]
    pd = rod["pitch"] / rod["d_clad_out"]
    Nu = nu_weisman(Re, w["Pr"], pd) if correlation == "weisman" else nu_dittus_boelter(Re, w["Pr"])
    h = Nu * w["k"] / D_e
    return dict(D_e=D_e, Re=Re, Pr=w["Pr"], Nu=Nu, h=h, props=w, pd=pd, correlation=correlation)


# %% [markdown]
# ## Resistances and the two limits
#
# $$R_{film} = \frac{1}{h\,\pi d_{co}}, \qquad R_{clad} = \frac{\ln(d_{co}/d_{ci})}{2\pi k_c}, \qquad
# R_{gap} = \frac{1}{h_{gap}\,\pi d_{ci}}, \qquad \int_{T_s}^{T_c} k_f\,dT = \frac{q'}{4\pi}$$
#
# The clad limit is a direct evaluation. The fuel limit is a fixed point on $q'$, because
# $T_s = T_b + q'(R_{film} + R_{clad} + R_{gap})$ depends on $q'$:
#
# $$q' \leftarrow 4\pi \int_{T_s(q')}^{2000\ °\mathrm{C}} k_f\,dT$$
#
# $k_c$ is evaluated at the mean clad temperature.

# %%
def clad_resistance(rod, T_clad_mean_C):
    d_ci = rod["d_clad_out"] - 2.0 * rod["t_clad"]
    k_c = k_zircaloy(T_clad_mean_C + 273.15)
    return math.log(rod["d_clad_out"] / d_ci) / (2.0 * math.pi * k_c), k_c


def gap_resistance(rod, h_gap):
    if not h_gap:
        return 0.0
    d_ci = rod["d_clad_out"] - 2.0 * rod["t_clad"]
    return 1.0 / (h_gap * math.pi * d_ci)


def _outer_chain(rod, q, R_film, R_gap):
    """Temperatures from the coolant to the pellet surface at linear heat rate q (W/m).
    Iterates k_clad at the mean clad temperature. Returns (T_clad_out, T_clad_in, T_surf, R_clad, k_c)."""
    T_co = rod["T_bulk"] + q * R_film
    T_ci = T_co + 20.0
    for _ in range(20):
        R_clad, k_c = clad_resistance(rod, 0.5 * (T_co + T_ci))
        T_ci_new = T_co + q * R_clad
        if abs(T_ci_new - T_ci) < 1e-6:
            T_ci = T_ci_new
            break
        T_ci = T_ci_new
    T_s = T_ci + q * R_gap
    return T_co, T_ci, T_s, R_clad, k_c


def centre_temperature(T_s_C, q):
    """Pellet centre temperature from ∫_{T_s}^{T_c} k dT = q/(4π), by bisection (°C)."""
    target = q / (4.0 * math.pi)
    lo, hi = T_s_C, 6000.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if k_uo2_integral(T_s_C + 273.15, mid + 273.15) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def solve_fuel_rod(T_bulk=None, h_gap=None, correlation="weisman", **overrides):
    rod = dict(ROD, **overrides)
    if T_bulk is not None:
        rod["T_bulk"] = T_bulk
    film = film_coefficient(rod, correlation)
    R_film = 1.0 / (film["h"] * math.pi * rod["d_clad_out"])
    R_gap = gap_resistance(rod, h_gap)

    # --- clad limit: hottest clad point is the inner surface
    q = 2.0e5
    for _ in range(50):
        _, T_ci, _, R_clad_c, _ = _outer_chain(rod, q, R_film, R_gap)
        q_new = (rod["T_clad_max"] - rod["T_bulk"]) / (R_film + R_clad_c)
        if abs(q_new - q) < 1e-6:
            break
        q = q_new
    q_clad = q

    # --- fuel limit: fixed point on q'
    q = 5.0e4
    history = []
    for _ in range(100):
        T_co, T_ci, T_s, R_clad, k_c = _outer_chain(rod, q, R_film, R_gap)
        q_new = 4.0 * math.pi * k_uo2_integral(T_s + 273.15, rod["T_fuel_max"] + 273.15)
        history.append((q, T_s, q_new))
        if abs(q_new - q) < 1e-6:
            q = q_new
            break
        q = q_new
    q_fuel = q
    T_co, T_ci, T_s, R_clad, k_c = _outer_chain(rod, q_fuel, R_film, R_gap)
    k_f_eff = k_uo2_effective(T_s, rod["T_fuel_max"])
    R_fuel = 1.0 / (4.0 * math.pi * k_f_eff)

    q_max = min(q_fuel, q_clad)
    return dict(rod=rod, film=film, h_gap=h_gap, R_film=R_film, R_clad=R_clad, R_gap=R_gap,
                R_fuel=R_fuel, k_clad=k_c, k_fuel_eff=k_f_eff, q_fuel=q_fuel, q_clad=q_clad,
                q_max=q_max, binding="pellet centre 2000 °C" if q_fuel < q_clad else "clad 1200 °C",
                history=history)


def temperatures(q, r):
    """Interface temperatures (°C) at linear heat rate q (W/m) for a solved case r."""
    rod = r["rod"]
    T_co, T_ci, T_s, R_clad, k_c = _outer_chain(rod, q, r["R_film"], r["R_gap"])
    T_c = centre_temperature(T_s, q)
    T_sat = r["film"]["props"]["T_sat"]
    # Jens-Lottes wall superheat if the clad surface is above saturation (subcooled boiling)
    q_flux = q / (math.pi * rod["d_clad_out"])
    dT_jl = 25.0 * (q_flux / 1e6) ** 0.25 * math.exp(-rod["P_bar"] / 62.0)
    return dict(T_bulk=rod["T_bulk"], T_clad_out=T_co, T_clad_in=T_ci, T_fuel_surface=T_s,
                T_centre=T_c, q_flux=q_flux, T_sat=T_sat, T_clad_out_boiling=T_sat + dT_jl,
                boiling=T_co > T_sat)


def radial_profile(q, r, n=60):
    """(radius mm, temperature °C) arrays through pellet, gap and clad at linear heat rate q."""
    rod = r["rod"]
    t = temperatures(q, r)
    r_p = rod["d_pellet"] / 2.0
    r_ci = rod["d_clad_out"] / 2.0 - rod["t_clad"]
    r_co = rod["d_clad_out"] / 2.0
    rr, TT = [], []
    # pellet: ∫_{T(r)}^{T_c} k dT = (q/4π)(1 − (r/r_p)²)  → bisection for T(r)
    for x in np.linspace(0.0, 1.0, n):
        target = q / (4.0 * math.pi) * (1.0 - x ** 2)
        lo, hi = t["T_fuel_surface"], t["T_centre"]
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            if k_uo2_integral(mid + 273.15, t["T_centre"] + 273.15, 401) < target:
                hi = mid
            else:
                lo = mid
        rr.append(x * r_p * 1e3)
        TT.append(0.5 * (lo + hi))
    # clad: logarithmic
    for x in np.linspace(r_ci, r_co, 10):
        rr.append(x * 1e3)
        TT.append(t["T_clad_in"] - (t["T_clad_in"] - t["T_clad_out"]) * math.log(x / r_ci) / math.log(r_co / r_ci))
    return np.array(rr), np.array(TT), t


# %% [markdown]
# ## Plant consistency check
#
# The core average coolant temperature (310 °C) is the mean of the Question 2 primary temperatures
# (295 → 325 °C). The plant power gives the primary flow. The unit cell gives the flow per rod,
# the number of rods and the core-average linear heat rate. The ratio $q'_{max}/q'_{avg}$ is the
# permitted total peaking factor.

# %%
def plant_check(r, plant=PLANT):
    rod = r["rod"]
    Q_th = plant["P_e_MW"] * 1e6 / plant["eta"]
    h_in = water_props(plant["T_core_in"], rod["P_bar"])["h"]
    h_out = water_props(plant["T_core_out"], rod["P_bar"])["h"]
    m_total = Q_th / (h_out - h_in)
    A_cell = flow_area_per_rod(rod["pitch"], rod["d_clad_out"])
    m_rod = r["film"]["props"]["rho"] * rod["V"] * A_cell
    N_rods = m_total / m_rod
    q_avg = Q_th / (N_rods * rod["L_active"])
    return dict(Q_th=Q_th, m_total=m_total, A_cell=A_cell, m_rod=m_rod, N_rods=N_rods,
                q_avg=q_avg, F_q_allowed=r["q_max"] / q_avg,
                P_rod_at_qmax=r["q_max"] * rod["L_active"] * 2.0 / math.pi)   # chopped cosine


def sensitivities(base):
    rows = [("Base case (Weisman, no gap, 310 °C)", base["q_max"])]
    rows.append(("Dittus–Boelter film", solve_fuel_rod(correlation="dittus")["q_max"]))
    rows.append(("Gap conductance 10 000 W/m²K", solve_fuel_rod(h_gap=1.0e4)["q_max"]))
    rows.append(("Gap conductance 5 000 W/m²K", solve_fuel_rod(h_gap=5.0e3)["q_max"]))
    rows.append(("Coolant 290 °C", solve_fuel_rod(T_bulk=290.0)["q_max"]))
    rows.append(("Coolant 330 °C", solve_fuel_rod(T_bulk=330.0)["q_max"]))
    return rows


def report(r=None):
    r = r or solve_fuel_rod()
    rod, f, w = r["rod"], r["film"], r["film"]["props"]
    t = temperatures(r["q_max"], r)
    tc = temperatures(r["q_clad"], r)
    print("=== Q1: maximum permissible linear heat rate ===")
    print(f"Sub-channel: D_e = {f['D_e']*1e3:.3f} mm, p/d = {f['pd']:.3f}, unit-cell flow area = {flow_area_per_rod(rod['pitch'], rod['d_clad_out'])*1e6:.2f} mm²")
    print(f"Water at {rod['T_bulk']:.0f} °C / {rod['P_bar']:.0f} bar: rho = {w['rho']:.1f} kg/m³, mu = {w['mu']*1e6:.2f} uPa s, k = {w['k']:.4f} W/mK, cp = {w['cp']:.0f} J/kgK, Pr = {w['Pr']:.3f}, T_sat = {w['T_sat']:.1f} °C")
    print(f"Re = {f['Re']:.4g}, Nu ({f['correlation']}) = {f['Nu']:.1f}, h = {f['h']:.0f} W/m²K")
    print(f"k_clad (MATPRO at mean clad T) = {r['k_clad']:.2f} W/mK, k_fuel effective = {r['k_fuel_eff']:.3f} W/mK")
    print(f"∫k_UO2 dT, 0 → 2840 °C = {k_uo2_integral(273.15, 2840+273.15)/100:.1f} W/cm (classic value 93 W/cm)")
    print("Resistances (K m/W): film {:.3e}, clad {:.3e}, gap {:.3e}, pellet {:.3e}, total {:.3e}".format(
        r["R_film"], r["R_clad"], r["R_gap"], r["R_fuel"], r["R_film"] + r["R_clad"] + r["R_gap"] + r["R_fuel"]))
    print(f"Pellet-centre limit: q'_fuel = {r['q_fuel']/1e3:.2f} kW/m   (fixed point converged in {len(r['history'])} passes)")
    print(f"Clad limit:          q'_clad = {r['q_clad']/1e3:.2f} kW/m")
    print(f"==> q'_max = {r['q_max']/1e3:.2f} kW/m, bound by the {r['binding']}")
    print(f"At q'_max: T_bulk {t['T_bulk']:.1f} → clad outer {t['T_clad_out']:.1f} → clad inner {t['T_clad_in']:.1f} → pellet surface {t['T_fuel_surface']:.1f} → centre {t['T_centre']:.1f} °C")
    print(f"   surface heat flux {t['q_flux']/1e6:.3f} MW/m²; clad outer {'above' if t['boiling'] else 'below'} T_sat = {t['T_sat']:.1f} °C"
          + (f" → subcooled nucleate boiling, Jens–Lottes wall {t['T_clad_out_boiling']:.1f} °C" if t['boiling'] else ""))
    print(f"At q'_clad (hypothetical): clad inner {tc['T_clad_in']:.0f} °C; the pellet centre would be far above the UO2 melting point (2840 °C)")
    pc = plant_check(r)
    print(f"Plant check: Q_th = {pc['Q_th']/1e6:.0f} MW, primary flow {pc['m_total']:.0f} kg/s, {pc['m_rod']:.3f} kg/s per rod → {pc['N_rods']:.0f} rods, "
          f"q'_avg = {pc['q_avg']/1e3:.2f} kW/m, allowable total peaking factor F_q = {pc['F_q_allowed']:.2f}")
    print(f"Rod power at q'_max with a chopped-cosine axial shape over {rod['L_active']:.0f} m: {pc['P_rod_at_qmax']/1e3:.1f} kW")
    print("Sensitivity of q'_max (kW/m):")
    for name, q in sensitivities(r):
        print(f"   {name:38s} {q/1e3:7.2f}")
    return r


# %% [main]
if __name__ == "__main__":
    report()
