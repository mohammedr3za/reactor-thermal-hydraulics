# %% [markdown]
# ## Design approach
#
# Segment-by-segment thermal-hydraulic design of one of the four once-through shell-and-tube
# steam generators of a 1000 MWe, 32 %-efficient PWR. Primary water flows down inside the tubes.
# Feedwater flows up on the shell side, parallel to the tubes, and leaves as superheated steam.
#
# Units: SI (Pa, J/kg, W/m²K), except pressures in function arguments in **bar** and
# temperatures in **°C**.

# %%
import math
from functools import lru_cache

import numpy as np
from iapws import IAPWS97
from iapws.iapws97 import _PSat_T

G0 = 9.80665  # m/s²

# ------------------------------------------------------------------ the specification as set
SPEC_GIVEN = dict(
    P_e_MW=1000.0, eta=0.32, n_loops=4,
    P_pri_bar=180.0, T_pri_in=325.0, T_pri_out=295.0,       # tube side (from Q1 / the plant)
    P_steam_bar=100.0, T_steam_out=320.0, dT_subcool=20.0,  # shell side
)

# ------------------------------------------------------------------ design choices
DESIGN = dict(
    d_o=15.875e-3,            # tube OD, m (5/8 in)
    pitch_ratio=1.3,          # triangular pitch / OD
    V_tube=3.5,               # target tube-side velocity, m/s  -> number of tubes
    S_allow=115e6,            # SS316 allowable stress, Pa (ASME II-D, ~650 °F)
    design_factor=1.1,        # design pressure / operating pressure
    E_joint=1.0,              # weld joint efficiency
    k_wall=17.5,              # SS316 conductivity, W/m K
    rho_metal=8000.0,         # SS316 density, kg/m³
    R_foul_in=2.5e-5,         # fouling, tube side, m²K/W
    R_foul_out=2.5e-5,        # fouling, shell side, m²K/W
    x_dryout=0.90,            # quality at dryout
    support_spacing=1.0,      # m between tube support plates
    K_support=0.5,            # loss coefficient per support plate (shell side)
    K_tube_ends=1.5,          # tube entrance + exit loss coefficient
    shell_clearance=0.05,     # diametral clearance between bundle and shell, m
    tube_count_factor=0.93,   # bundle area utilisation
    n_segments=40,            # segments reported (at least 20)
    dz_fine=0.1,              # m, fine march that fixes the length
    L_max=60.0,               # m, abort limit
    t_support=0.025,          # support plate thickness, m
    support_solid_fraction=0.5,
    allowance=0.10,           # nozzles, skirt, internals
)

BWG = [(22, 0.711e-3), (20, 0.889e-3), (19, 1.067e-3), (18, 1.245e-3), (17, 1.473e-3),
       (16, 1.651e-3), (15, 1.829e-3), (14, 2.108e-3), (13, 2.413e-3), (12, 2.769e-3),
       (11, 3.048e-3), (10, 3.404e-3)]


# %% [markdown]
# ## Water and steam properties (IAPWS-IF97)
#
# One wrapper for every property call. Saturation properties are cached per pressure.

# %%
def _pack(w):
    return dict(T=w.T - 273.15, P=w.P * 10.0, h=w.h * 1e3, rho=w.rho, mu=w.mu, k=w.k,
                cp=None if w.cp is None else w.cp * 1e3, Pr=w.Prandt, x=w.x, region=w.region)


def state_PT(P_bar, T_C):
    return _pack(IAPWS97(P=P_bar / 10.0, T=T_C + 273.15))


def state_Ph(P_bar, h):
    return _pack(IAPWS97(P=P_bar / 10.0, h=h / 1e3))


@lru_cache(maxsize=None)
def saturation(P_bar):
    f = IAPWS97(P=P_bar / 10.0, x=0.0)
    g = IAPWS97(P=P_bar / 10.0, x=1.0)
    return dict(P=P_bar, Tsat=f.T - 273.15, hf=f.h * 1e3, hg=g.h * 1e3, hfg=(g.h - f.h) * 1e3,
                rhof=f.rho, rhog=g.rho, muf=f.mu, mug=g.mu, kf=f.k, kg=g.k,
                cpf=f.cp * 1e3, cpg=g.cp * 1e3, Prf=f.Prandt, Prg=g.Prandt, sigma=f.sigma)


def sat_at(P_bar):
    return saturation(round(P_bar, 4))


def psat_T(T_C):
    """Saturation pressure (Pa) at T (°C)."""
    return _PSat_T(T_C + 273.15) * 1e6


def mixture_density(P_bar, h, sat):
    if sat["hf"] <= h <= sat["hg"]:
        x = (h - sat["hf"]) / sat["hfg"]
        return 1.0 / (x / sat["rhog"] + (1.0 - x) / sat["rhof"])
    return state_Ph(P_bar, h)["rho"]


# %% [markdown]
# ## Energy balance and feasibility
#
# $$Q_{SG} = \frac{P_e}{\eta\,N_{loops}}, \qquad \dot m_p = \frac{Q_{SG}}{h_{p,in} - h_{p,out}}, \qquad
# \dot m_s = \frac{Q_{SG}}{h_{s,out} - h_{fw}}$$
#
# The T–Q diagram needs no heat-transfer model. With $Q$ the heat transferred from the cold end:
#
# $$h_p(Q) = h_{p,out} + \frac{Q}{\dot m_p}, \qquad h_s(Q) = h_{fw} + \frac{Q}{\dot m_s}, \qquad
# \Delta T(Q) = T_p(Q) - T_s(Q)$$
#
# The approach at the onset of boiling is $\Delta T$ at $Q = \dot m_s(h_f - h_{fw})$. It must be
# positive; the design requires 10 K.

# %%
def energy_balance(spec, P_shell_in=None):
    Q_th = spec["P_e_MW"] * 1e6 / spec["eta"]
    Q_sg = Q_th / spec["n_loops"]
    p_in = state_PT(spec["P_pri_bar"], spec["T_pri_in"])
    p_out = state_PT(spec["P_pri_bar"], spec["T_pri_out"])
    m_pri = Q_sg / (p_in["h"] - p_out["h"])
    P_in = spec["P_steam_bar"] if P_shell_in is None else P_shell_in
    sat_in = sat_at(P_in)
    T_fw = sat_in["Tsat"] - spec["dT_subcool"]
    fw = state_PT(P_in, T_fw)
    out = state_PT(spec["P_steam_bar"], spec["T_steam_out"])
    sat_out = sat_at(spec["P_steam_bar"])
    dh = out["h"] - fw["h"]
    m_sec = Q_sg / dh
    return dict(Q_th=Q_th, Q_sg=Q_sg, m_pri=m_pri, m_sec=m_sec,
                h_pri_in=p_in["h"], h_pri_out=p_out["h"], cp_pri_mean=(p_in["h"] - p_out["h"]) / (spec["T_pri_in"] - spec["T_pri_out"]),
                h_fw=fw["h"], T_fw=T_fw, h_sec_out=out["h"], P_shell_in=P_in,
                Tsat_out=sat_out["Tsat"], superheat=spec["T_steam_out"] - sat_out["Tsat"],
                f_pre=(sat_out["hf"] - fw["h"]) / dh, f_boil=sat_out["hfg"] / dh, f_sh=(out["h"] - sat_out["hg"]) / dh)


def pinch_analysis(spec, n=400):
    """T–Q diagram. dT_min is the overall minimum approach; dT_boil the approach where the
    secondary reaches saturation (the pressure-dependent pinch); dT_hot/dT_cold the terminal
    differences."""
    eb = energy_balance(spec)
    Q = np.linspace(0.0, eb["Q_sg"], n)
    T_p = np.array([state_Ph(spec["P_pri_bar"], eb["h_pri_out"] + q / eb["m_pri"])["T"] for q in Q])
    T_s = np.array([state_Ph(spec["P_steam_bar"], eb["h_fw"] + q / eb["m_sec"])["T"] for q in Q])
    dT = T_p - T_s
    i = int(np.argmin(dT))
    sat = sat_at(spec["P_steam_bar"])
    Q_boil = eb["m_sec"] * (sat["hf"] - eb["h_fw"])
    T_p_boil = state_Ph(spec["P_pri_bar"], eb["h_pri_out"] + Q_boil / eb["m_pri"])["T"]
    return dict(Q=Q, T_pri=T_p, T_sec=T_s, dT=dT, dT_min=float(dT[i]), Q_at_min=float(Q[i]),
                frac_at_min=float(Q[i] / eb["Q_sg"]), eb=eb,
                dT_boil=T_p_boil - sat["Tsat"], frac_boil=Q_boil / eb["Q_sg"], T_pri_boil=T_p_boil,
                dT_hot=spec["T_pri_in"] - spec["T_steam_out"], dT_cold=spec["T_pri_out"] - eb["T_fw"])


def max_feasible_steam_pressure(spec, dT_pinch_min=10.0, lo=30.0, hi=110.0, tol=0.01):
    """Largest steam pressure (bar) that keeps an approach of dT_pinch_min at the onset of boiling."""
    def margin(P):
        return pinch_analysis(dict(spec, P_steam_bar=P), n=150)["dT_boil"] - dT_pinch_min
    if margin(lo) < 0:
        raise ValueError("no feasible pressure above %.0f bar" % lo)
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if margin(mid) > 0:
            lo = mid
        else:
            hi = mid
    return lo


# %% [markdown]
# ## Mechanical sizing (ASME VIII thin wall)
#
# $$t_{tube} = \frac{P\,d_o}{2SE + 0.8P}, \qquad t_{shell} = \frac{P\,R}{SE - 0.6P}, \qquad
# t_{head} = \frac{P\,R}{2SE - 0.2P}, \qquad T_{ts} = \frac{D}{3}\sqrt{\frac{P}{S}}$$
#
# The tube wall is rounded up to a BWG gauge.

# %%
def asme_tube_thickness(d_o, P, S, E=1.0):
    return P * d_o / (2.0 * S * E + 0.8 * P)


def round_up_bwg(t):
    for gauge, wall in BWG:
        if wall >= t - 1e-9:
            return wall
    raise ValueError("wall thicker than BWG 10")


def bwg_gauge(wall):
    return next(g for g, w in BWG if abs(w - wall) < 1e-9)


def asme_shell_thickness(D_i, P, S, E=1.0):
    return P * (D_i / 2.0) / (S * E - 0.6 * P)


def asme_head_thickness(D_i, P, S, E=1.0):
    return P * (D_i / 2.0) / (2.0 * S * E - 0.2 * P)


def tubesheet_thickness(D, P, S):
    return (D / 3.0) * math.sqrt(P / S)


# %% [markdown]
# ## Heat-transfer and friction correlations
#
# Single phase (Dittus–Boelter), $n$ = 0.3 cooling, 0.4 heating:
# $$\mathrm{Nu} = 0.023\,\mathrm{Re}^{0.8}\,\mathrm{Pr}^{n}$$
#
# Boiling (Chen 1966):
# $$h_{TP} = F\,h_l + S\,h_{FZ}, \qquad h_l = 0.023\,\mathrm{Re}_l^{0.8}\,\mathrm{Pr}_l^{0.4}\,\frac{k_l}{D}, \qquad
# \mathrm{Re}_l = \frac{G(1-x)D}{\mu_l}$$
# $$\frac{1}{X_{tt}} = \left(\frac{x}{1-x}\right)^{0.9}\left(\frac{\rho_l}{\rho_g}\right)^{0.5}\left(\frac{\mu_g}{\mu_l}\right)^{0.1}, \qquad
# F = \begin{cases} 1 & 1/X_{tt} \le 0.1 \\ 2.35\,(1/X_{tt} + 0.213)^{0.736} & 1/X_{tt} > 0.1 \end{cases}$$
# $$S = \frac{1}{1 + 2.53\times10^{-6}(\mathrm{Re}_l F^{1.25})^{1.17}}, \qquad
# h_{FZ} = 0.00122\,\frac{k_l^{0.79} c_{p,l}^{0.45} \rho_l^{0.49}}{\sigma^{0.5} \mu_l^{0.29} h_{fg}^{0.24} \rho_g^{0.24}}\,
# \Delta T_{sat}^{0.24}\,\Delta p_{sat}^{0.75}$$
#
# Post-dryout (Dougall–Rohsenow, thermal equilibrium):
# $$h = 0.023\,\frac{k_g}{D}\left[\frac{GD}{\mu_g}\left(x + \frac{\rho_g}{\rho_l}(1-x)\right)\right]^{0.8}\mathrm{Pr}_g^{0.4}$$
#
# Friction (Filonenko, Darcy, smooth):
# $$f = (0.79\,\ln\mathrm{Re} - 1.64)^{-2}$$

# %%
def nu_dittus_boelter(Re, Pr, n=0.4):
    return 0.023 * Re ** 0.8 * Pr ** n


def friction_factor(Re):
    if Re < 2300.0:
        return 64.0 / Re
    return (0.79 * math.log(Re) - 1.64) ** -2


def chen(G, x, D, sat, dT_wall, P_bar=None):
    """Chen (1966) boiling coefficient. dT_wall = T_surface − T_sat (K, >= 0).
    Returns the pieces: liquid-only h_l, F, S, h_conv = F h_l, h_nb = S h_FZ and their sum."""
    x = min(max(x, 0.0), 1.0 - 1e-9)
    Re_l = G * (1.0 - x) * D / sat["muf"]
    h_l = nu_dittus_boelter(Re_l, sat["Prf"], 0.4) * sat["kf"] / D
    if x <= 0.0:
        Xtt_inv = 0.0
    else:
        Xtt_inv = (x / (1.0 - x)) ** 0.9 * (sat["rhof"] / sat["rhog"]) ** 0.5 * (sat["mug"] / sat["muf"]) ** 0.1
    F = 1.0 if Xtt_inv <= 0.1 else 2.35 * (Xtt_inv + 0.213) ** 0.736
    Re_tp = Re_l * F ** 1.25
    S = 1.0 / (1.0 + 2.53e-6 * Re_tp ** 1.17)
    if dT_wall > 0.0:
        P = sat["P"] * 1e5 if P_bar is None else P_bar * 1e5
        dp_sat = max(psat_T(sat["Tsat"] + dT_wall) - P, 0.0)
        h_fz = 0.00122 * (sat["kf"] ** 0.79 * sat["cpf"] ** 0.45 * sat["rhof"] ** 0.49
                          / (sat["sigma"] ** 0.5 * sat["muf"] ** 0.29 * sat["hfg"] ** 0.24 * sat["rhog"] ** 0.24)) \
            * dT_wall ** 0.24 * dp_sat ** 0.75
    else:
        h_fz = 0.0
    return dict(h_l=h_l, F=F, S=S, h_conv=F * h_l, h_nb=S * h_fz, h=F * h_l + S * h_fz, Re_l=Re_l, Xtt_inv=Xtt_inv)


def dougall_rohsenow(G, x, D, sat):
    Re_g = G * D / sat["mug"] * (x + (sat["rhog"] / sat["rhof"]) * (1.0 - x))
    return nu_dittus_boelter(Re_g, sat["Prg"], 0.4) * sat["kg"] / D


# %% [markdown]
# ## Geometry from the design choices
#
# $$N = \left\lceil\frac{\dot m_p}{\rho_p V_t A_i}\right\rceil, \qquad
# A_{free} = \frac{\sqrt{3}}{2}p^2 - \frac{\pi}{4}d_o^2, \qquad G_s = \frac{\dot m_s}{N A_{free}}, \qquad
# D_e = d_o\left[\frac{2\sqrt{3}}{\pi}\left(\frac{p}{d_o}\right)^2 - 1\right]$$

# %%
def geometry(spec, design, eb):
    d_o = design["d_o"]
    P_tube_design = design["design_factor"] * spec["P_pri_bar"] * 1e5
    t_min = asme_tube_thickness(d_o, P_tube_design, design["S_allow"], design["E_joint"])
    t_tube = round_up_bwg(t_min)
    d_i = d_o - 2.0 * t_tube
    A_i = math.pi * d_i ** 2 / 4.0
    pri_mean = state_PT(spec["P_pri_bar"], 0.5 * (spec["T_pri_in"] + spec["T_pri_out"]))
    N = int(math.ceil(eb["m_pri"] / (pri_mean["rho"] * design["V_tube"] * A_i)))
    G_t = eb["m_pri"] / (N * A_i)
    pitch = design["pitch_ratio"] * d_o
    A_cell = (math.sqrt(3.0) / 2.0) * pitch ** 2
    A_free = A_cell - math.pi * d_o ** 2 / 4.0
    A_shell_flow = N * A_free
    D_e = d_o * ((2.0 * math.sqrt(3.0) / math.pi) * design["pitch_ratio"] ** 2 - 1.0)
    D_otl = math.sqrt(4.0 * N * A_cell / (math.pi * design["tube_count_factor"]))
    D_shell = D_otl + design["shell_clearance"]
    R_wall = d_o * math.log(d_o / d_i) / (2.0 * design["k_wall"])
    return dict(d_o=d_o, d_i=d_i, t_tube=t_tube, t_tube_min=t_min, gauge=bwg_gauge(t_tube),
                P_tube_design=P_tube_design, A_i=A_i, N=N, G_t=G_t, V_t=G_t / pri_mean["rho"],
                pitch=pitch, A_cell=A_cell, A_free=A_free, A_shell_flow=A_shell_flow,
                G_s=eb["m_sec"] / A_shell_flow, D_e=D_e, D_otl=D_otl, D_shell=D_shell,
                R_wall=R_wall, A_ht_per_m=N * math.pi * d_o, rho_pri_mean=pri_mean["rho"])


# %% [markdown]
# ## Local heat flux at one axial position
#
# All resistances refer to the outer tube surface:
#
# $$q'' = \frac{T_p - T_w}{R_{in}} = q''_{shell}(T_w), \qquad
# R_{in} = \frac{d_o}{d_i}\left(\frac{1}{h_i} + R_{f,i}\right) + \frac{d_o\ln(d_o/d_i)}{2k_w} + R_{f,o}$$
#
# $T_w$ is found by bisection, because the Chen nucleate term depends on the wall superheat.
# $U = q''/(T_p - T_s)$.

# %%
def evaluate_local(spec, design, geom, T_p, P_s, h_s):
    sat = sat_at(P_s)
    pri = state_PT(spec["P_pri_bar"], T_p)
    Re_t = geom["G_t"] * geom["d_i"] / pri["mu"]
    h_i = nu_dittus_boelter(Re_t, pri["Pr"], 0.3) * pri["k"] / geom["d_i"]
    ratio = geom["d_o"] / geom["d_i"]
    R_in = ratio * (1.0 / h_i + design["R_foul_in"]) + geom["R_wall"] + design["R_foul_out"]

    G_s, D_e = geom["G_s"], geom["D_e"]
    if h_s < sat["hf"]:
        regime, x = "subcooled", 0.0
        liq = state_Ph(P_s, h_s)
        if liq["mu"] is None:                      # landed on the saturation line
            liq = dict(liq, mu=sat["muf"], k=sat["kf"], Pr=sat["Prf"], rho=sat["rhof"])
        T_b = liq["T"]
        h_l = nu_dittus_boelter(G_s * D_e / liq["mu"], liq["Pr"], 0.4) * liq["k"] / D_e
        rho_H, mu_H = liq["rho"], liq["mu"]

        def q_shell(T_surf):
            q = h_l * (T_surf - T_b)
            if T_surf > sat["Tsat"]:
                q += chen(G_s, 0.0, D_e, sat, T_surf - sat["Tsat"])["h_nb"] * (T_surf - sat["Tsat"])
            return q
    elif h_s <= sat["hg"]:
        x = (h_s - sat["hf"]) / sat["hfg"]
        T_b = sat["Tsat"]
        rho_H = 1.0 / (x / sat["rhog"] + (1.0 - x) / sat["rhof"])
        mu_H = 1.0 / (x / sat["mug"] + (1.0 - x) / sat["muf"])
        if x < design["x_dryout"]:
            regime = "nucleate boiling"

            def q_shell(T_surf):
                return chen(G_s, x, D_e, sat, max(T_surf - T_b, 0.0))["h"] * (T_surf - T_b)
        else:
            regime = "post-dryout"
            h_pdo = dougall_rohsenow(G_s, x, D_e, sat)

            def q_shell(T_surf):
                return h_pdo * (T_surf - T_b)
    else:
        regime, x = "superheated", 1.0
        vap = state_Ph(P_s, h_s)
        T_b = vap["T"]
        h_v = nu_dittus_boelter(G_s * D_e / vap["mu"], vap["Pr"], 0.4) * vap["k"] / D_e
        rho_H, mu_H = vap["rho"], vap["mu"]

        def q_shell(T_surf):
            return h_v * (T_surf - T_b)

    lo, hi = T_b, T_p
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if (T_p - mid) / R_in - q_shell(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    T_surf = 0.5 * (lo + hi)
    q = (T_p - T_surf) / R_in
    T_wo = T_surf + q * design["R_foul_out"]
    T_wi = T_wo + q * geom["R_wall"]
    Re_s = G_s * D_e / mu_H
    f_s = friction_factor(Re_s)
    return dict(regime=regime, x=x, T_pri=T_p, T_sec=T_b, T_surf=T_surf, T_wall_out=T_wo,
                T_wall_in=T_wi, q=q, U=q / (T_p - T_b), h_i=h_i, h_o=q / max(T_surf - T_b, 1e-9),
                Re_t=Re_t, Re_s=Re_s, rho_H=rho_H, f_s=f_s, f_t=friction_factor(Re_t),
                rho_pri=pri["rho"], dpdz_f=f_s / D_e * G_s ** 2 / (2.0 * rho_H), dpdz_g=rho_H * G0,
                Tsat=sat["Tsat"], P_sec=P_s, h_sec=h_s)


# %% [markdown]
# ## The axial march
#
# Both streams are known at the bottom (primary outlet, feedwater inlet). The march starts there:
#
# $$\Delta Q_i = q''_i\,N\pi d_o\,\Delta z, \qquad h_{s,i+1} = h_{s,i} + \frac{\Delta Q_i}{\dot m_s}, \qquad
# h_{p,i+1} = h_{p,i} + \frac{\Delta Q_i}{\dot m_p}$$
#
# Shell-side pressure drop per segment, homogeneous two-phase model:
#
# $$\Delta p = f\,\frac{\Delta z}{D_e}\,\frac{G_s^2}{2\rho_H} + \rho_H g\,\Delta z + G_s^2\,\Delta\!\left(\frac{1}{\rho_H}\right) + K\,\frac{G_s^2}{2\rho_H},
# \qquad \frac{1}{\rho_H} = \frac{x}{\rho_g} + \frac{1-x}{\rho_l}$$
#
# Each segment uses the midpoint rule and is sub-stepped at regime boundaries. The march ends
# when the secondary reaches the outlet enthalpy. The height is the result. The primary reaches
# its inlet temperature at the same point by energy conservation.

# %%
def _regime_boundaries(sat, design):
    return (sat["hf"], sat["hf"] + design["x_dryout"] * sat["hfg"], sat["hg"])


def _advance(spec, design, geom, eb, st, dz):
    """Advance the secondary/primary state by at most dz, stopping at a regime boundary or the
    outlet. Midpoint (RK2) rule with two corrector passes. Returns (new state, record)."""
    z, h_s, h_p, P_s, rho_in = st
    m_s, m_p, A_m, G_s = eb["m_sec"], eb["m_pri"], geom["A_ht_per_m"], geom["G_s"]
    sat = sat_at(P_s)
    T_p = state_Ph(spec["P_pri_bar"], h_p)["T"]
    loc1 = evaluate_local(spec, design, geom, T_p, P_s, h_s)
    h_lim = min([b for b in _regime_boundaries(sat, design) if b > h_s + 1e-6] + [eb["h_sec_out"]])
    loc, dz_eff, limited = loc1, dz, False
    for _ in range(2):
        dz_eff = min(dz, (h_lim - h_s) * m_s / (loc["q"] * A_m))
        limited = dz_eff < dz
        dQ = loc["q"] * A_m * dz_eff
        T_p_m = state_Ph(spec["P_pri_bar"], h_p + 0.5 * dQ / m_p)["T"]
        P_s_m = P_s - 0.5 * (loc["dpdz_f"] + loc["dpdz_g"]) * dz_eff / 1e5
        loc = evaluate_local(spec, design, geom, T_p_m, P_s_m, h_s + 0.5 * dQ / m_s)
    if limited:
        dQ = (h_lim - h_s) * m_s                       # land exactly on the boundary / outlet
        dz_eff = dQ / (loc["q"] * A_m)
    else:
        dQ = loc["q"] * A_m * dz_eff
    h_s_new, h_p_new = h_s + dQ / m_s, h_p + dQ / m_p
    rho_out = mixture_density(P_s, h_s_new, sat)
    n_sp = math.floor((z + dz_eff) / design["support_spacing"]) - math.floor(z / design["support_spacing"])
    dP = dict(dP_f=loc["dpdz_f"] * dz_eff, dP_g=loc["dpdz_g"] * dz_eff,
              dP_a=G_s ** 2 * (1.0 / rho_out - 1.0 / rho_in),
              dP_sp=n_sp * design["K_support"] * G_s ** 2 / (2.0 * loc["rho_H"]))
    new = (z + dz_eff, h_s_new, h_p_new, P_s - sum(dP.values()) / 1e5, rho_out)
    return new, dict(inlet=loc1, dz=dz_eff, dQ=dQ, **dP)


def march(spec, design, geom, eb, dz):
    """Equal-height segments from the bottom up; each segment is integrated in sub-steps that
    stop at regime boundaries so the scheme stays second order. Each record holds the actual
    state at the segment inlet plus the segment totals."""
    st = (0.0, eb["h_fw"], eb["h_pri_out"], eb["P_shell_in"], mixture_density(eb["P_shell_in"], eb["h_fw"], sat_at(eb["P_shell_in"])))
    segs = []
    while st[1] < eb["h_sec_out"] - 1e-9:
        if st[0] > design["L_max"]:
            raise RuntimeError("march exceeded L_max = %.0f m: the design cannot reach the outlet state" % design["L_max"])
        z0, z_target = st[0], st[0] + dz
        first, tot = None, dict(dQ=0.0, dP_f=0.0, dP_g=0.0, dP_a=0.0, dP_sp=0.0)
        while st[0] < z_target - 1e-9 and st[1] < eb["h_sec_out"] - 1e-9:
            st, rec = _advance(spec, design, geom, eb, st, z_target - st[0])
            first = first or rec["inlet"]
            for k in tot:
                tot[k] += rec[k]
        segs.append(dict(first, z0=z0, z1=st[0], z=z0, dz=st[0] - z0, dP=sum(v for k, v in tot.items() if k != "dQ"), **tot))
    z, h_s, h_p, P_s, _ = st
    T_p = state_Ph(spec["P_pri_bar"], h_p)["T"]
    top = evaluate_local(spec, design, geom, T_p, P_s, h_s)
    return dict(L=z, segments=segs, top=top, P_sec_out=P_s, T_pri_top=T_p, T_sec_top=top["T_sec"])


def run_march(spec, design, geom, dz, n_outer=3):
    """March with the shell inlet pressure iterated so the outlet lands on the specified pressure."""
    P_in = spec["P_steam_bar"]
    for _ in range(n_outer):
        eb = energy_balance(spec, P_shell_in=P_in)
        geom = dict(geom, G_s=eb["m_sec"] / geom["A_shell_flow"])
        res = march(spec, design, geom, eb, dz)
        P_in += spec["P_steam_bar"] - res["P_sec_out"]
    return res, eb, geom


# %% [markdown]
# ## The complete design

# %%
def _columns(segs):
    keys = [k for k in segs[0] if not isinstance(segs[0][k], str)]
    out = {k: np.array([s[k] for s in segs]) for k in keys}
    out["regime"] = [s["regime"] for s in segs]
    return out


def design(spec, design=None):
    dsg = dict(DESIGN, **(design or {}))
    pa = pinch_analysis(spec, n=200)
    if pa["dT_min"] <= 0.0:
        raise ValueError("infeasible specification: minimum approach %.1f K (temperature cross at %.0f %% of the duty)"
                         % (pa["dT_min"], 100 * pa["frac_at_min"]))
    eb0 = energy_balance(spec)
    geom = geometry(spec, dsg, eb0)
    fine, eb, geom = run_march(spec, dsg, geom, dz=dsg["dz_fine"])
    rep, eb, geom = run_march(spec, dsg, geom, dz=fine["L"] / dsg["n_segments"])
    seg = _columns(rep["segments"])
    L = rep["L"]
    S, E, rho_m = dsg["S_allow"], dsg["E_joint"], dsg["rho_metal"]

    # --- shell, heads, tubesheets
    P_shell_design = dsg["design_factor"] * eb["P_shell_in"] * 1e5
    t_shell = asme_shell_thickness(geom["D_shell"], P_shell_design, S, E)
    t_head = asme_head_thickness(geom["D_shell"], geom["P_tube_design"], S, E)      # primary plenums
    t_ts = tubesheet_thickness(geom["D_shell"], geom["P_tube_design"], S)
    n_sp = int(math.floor(L / dsg["support_spacing"]))

    # --- tube-side pressure drop (downflow)
    G_t, d_i = geom["G_t"], geom["d_i"]
    dP_t_fric = float(np.sum(seg["f_t"] * seg["dz"] / d_i * G_t ** 2 / (2.0 * seg["rho_pri"])))
    rho_p_mean = float(np.mean(seg["rho_pri"]))
    dP_t_ends = dsg["K_tube_ends"] * G_t ** 2 / (2.0 * rho_p_mean)
    dP_t_grav = -rho_p_mean * G0 * L
    # --- shell-side pressure drop (upflow)
    dP_s = dict(friction=float(np.sum(seg["dP_f"])), gravity=float(np.sum(seg["dP_g"])),
                acceleration=float(np.sum(seg["dP_a"])), supports=float(np.sum(seg["dP_sp"])))
    dP_shell = sum(dP_s.values())

    # --- weights (dry)
    N, d_o, D_s = geom["N"], geom["d_o"], geom["D_shell"]
    L_shell = L + 2.0 * t_ts
    w = dict(tubes=N * math.pi / 4.0 * (d_o ** 2 - d_i ** 2) * L * rho_m,
             shell=math.pi * (D_s + t_shell) * t_shell * L_shell * rho_m,
             heads=2.0 * 2.0 * math.pi * (D_s / 2.0 + t_head / 2.0) ** 2 * t_head * rho_m,
             tubesheets=2.0 * (math.pi / 4.0 * D_s ** 2 - N * math.pi / 4.0 * d_o ** 2) * t_ts * rho_m,
             supports=n_sp * math.pi / 4.0 * D_s ** 2 * dsg["t_support"] * dsg["support_solid_fraction"] * rho_m)
    w["subtotal"] = sum(w.values())
    w["allowance"] = dsg["allowance"] * w["subtotal"]
    weight = w["subtotal"] + w["allowance"]

    A_total = geom["A_ht_per_m"] * L
    return dict(spec=spec, design=dsg, eb=eb, geom=geom, pinch=pa, segments=seg, fine=fine, report=rep,
                N_tubes=N, d_o=d_o, d_i=d_i, t_tube=geom["t_tube"], gauge=geom["gauge"], L_tube=L, L_fine=fine["L"],
                D_shell=D_s, D_otl=geom["D_otl"], t_shell=t_shell, t_head=t_head, t_tubesheet=t_ts, n_supports=n_sp,
                H_overall=L_shell + 2.0 * (D_s / 2.0 + t_head),
                dP_shell=dP_shell, dP_shell_parts=dP_s,
                dP_tube=dP_t_fric + dP_t_ends, dP_tube_parts=dict(friction=dP_t_fric, ends=dP_t_ends, gravity=dP_t_grav),
                dP_tube_net=dP_t_fric + dP_t_ends + dP_t_grav,
                weight=weight, weights=w, A_total=A_total, U_mean=eb["Q_sg"] / A_total / float(np.average(seg["T_pri"] - seg["T_sec"], weights=seg["dz"])),
                q_mean=eb["Q_sg"] / A_total)


# %% [markdown]
# ## Design-space sweeps

# %%
def tradeoff(spec, dsg=None, V_list=(3.0, 4.0, 5.0, 6.0)):
    rows = []
    for V in V_list:
        r = design(spec, dict(dsg or {}, V_tube=V))
        rows.append(dict(V=V, V_actual=r["geom"]["V_t"], N=r["N_tubes"], L=r["L_tube"], D_shell=r["D_shell"],
                         dP_tube=r["dP_tube"], dP_shell=r["dP_shell"], weight=r["weight"], A=r["A_total"]))
    return rows


def convergence(spec, dsg=None, ns=(20, 40, 80)):
    rows = []
    for n in ns:
        r = design(spec, dict(dsg or {}, n_segments=n))
        rows.append(dict(n=n, L=r["L_tube"], L_fine=r["L_fine"], T_pri_top=r["report"]["T_pri_top"], T_sec_top=r["report"]["T_sec_top"]))
    return rows


def alternatives(spec_given, dT_pinch_min=10.0):
    """How the infeasible spec could be rescued, with the resulting pinch."""
    P_max = max_feasible_steam_pressure(spec_given, dT_pinch_min)
    rows = [("As set: 100 bar steam, primary 325/295 °C", spec_given)]
    P_adopt = 5.0 * math.floor(P_max / 5.0)
    rows.append((f"Steam pressure lowered to {P_adopt:.0f} bar (adopted)", dict(spec_given, P_steam_bar=P_adopt)))
    rows.append(("Keep 100 bar, primary raised to 345/315 °C", dict(spec_given, T_pri_in=345.0, T_pri_out=315.0)))
    rows.append(("Keep 100 bar, primary 325/318 °C (4.3× flow)", dict(spec_given, T_pri_out=318.0)))
    out = []
    for name, sp in rows:
        pa = pinch_analysis(sp, n=400)
        out.append(dict(name=name, P=sp["P_steam_bar"], T_in=sp["T_pri_in"], T_out=sp["T_pri_out"],
                        Tsat=pa["eb"]["Tsat_out"], dT_min=pa["dT_min"], frac=pa["frac_at_min"], m_pri=pa["eb"]["m_pri"]))
    return out, P_max


# %% [markdown]
# ## Printed report

# %%
def segment_table(r, every=1):
    s, top = r["segments"], r["report"]["top"]
    hdr = "  #   z0[m]  T_pri  T_sec  T_wo   x     h_i    h_o     U    q''[kW/m²] P_sec[bar]  dQ[MW]  regime"
    fmt = "%3s %7.2f %6.1f %6.1f %6.1f %5.3f %6.0f %7.0f %6.0f %9.1f %10.2f %7.2f  %s"
    lines = [hdr]
    for i in range(0, len(s["z"]), every):
        lines.append(fmt % (i + 1, s["z0"][i], s["T_pri"][i], s["T_sec"][i], s["T_wall_out"][i], s["x"][i], s["h_i"][i],
                            s["h_o"][i], s["U"][i], s["q"][i] / 1e3, s["P_sec"][i], s["dQ"][i] / 1e6, s["regime"][i]))
    lines.append(fmt % ("top", r["L_tube"], top["T_pri"], top["T_sec"], top["T_wall_out"], top["x"], top["h_i"], top["h_o"],
                        top["U"], top["q"] / 1e3, top["P_sec"], 0.0, top["regime"]))
    return "\n".join(lines)


def report(r):
    sp, eb, g, w = r["spec"], r["eb"], r["geom"], r["weights"]
    print("=== Q2: once-through steam generator, one of %d loops ===" % sp["n_loops"])
    print(f"Duty {eb['Q_sg']/1e6:.2f} MW per SG (plant {eb['Q_th']/1e6:.0f} MWth)")
    print(f"Primary: {sp['P_pri_bar']:.0f} bar, {sp['T_pri_in']:.0f} → {sp['T_pri_out']:.0f} °C, m = {eb['m_pri']:.0f} kg/s")
    print(f"Secondary: feed {eb['T_fw']:.1f} °C at {eb['P_shell_in']:.2f} bar → steam {sp['T_steam_out']:.0f} °C at {sp['P_steam_bar']:.0f} bar "
          f"(T_sat {eb['Tsat_out']:.1f} °C, superheat {eb['superheat']:.1f} K), m = {eb['m_sec']:.1f} kg/s")
    print(f"Duty split: preheat {100*eb['f_pre']:.1f} %, boiling {100*eb['f_boil']:.1f} %, superheat {100*eb['f_sh']:.1f} %; "
          f"approach {r['pinch']['dT_boil']:.1f} K at the onset of boiling, {r['pinch']['dT_hot']:.1f} K at the hot end, {r['pinch']['dT_cold']:.1f} K at the cold end")
    print(f"(i)   Number of tubes: {r['N_tubes']}  (tube-side velocity {g['V_t']:.2f} m/s, G = {g['G_t']:.0f} kg/m²s)")
    print(f"(ii)  Tubes: OD {r['d_o']*1e3:.3f} mm, wall {r['t_tube']*1e3:.3f} mm (BWG {r['gauge']}, ASME minimum {g['t_tube_min']*1e3:.3f} mm), "
          f"ID {r['d_i']*1e3:.2f} mm, height {r['L_tube']:.2f} m (fine march {r['L_fine']:.2f} m)")
    print(f"      Triangular pitch {g['pitch']*1e3:.2f} mm, shell-side D_e = {g['D_e']*1e3:.2f} mm, G_shell = {g['G_s']:.0f} kg/m²s, "
          f"heat-transfer area {r['A_total']:.0f} m², mean U {r['U_mean']:.0f} W/m²K, mean flux {r['q_mean']/1e3:.1f} kW/m²")
    print(f"(iii) Shell: bundle (OTL) diameter {r['D_otl']:.2f} m, shell ID {r['D_shell']:.2f} m, shell wall {r['t_shell']*1e3:.0f} mm; "
          f"heads {r['t_head']*1e3:.0f} mm, tubesheets {r['t_tubesheet']*1e3:.0f} mm, {r['n_supports']} support plates, overall height {r['H_overall']:.1f} m")
    p = r["dP_shell_parts"]
    print(f"(iv)  Shell-side ΔP = {r['dP_shell']/1e5:.3f} bar (friction {p['friction']/1e5:.3f}, gravity {p['gravity']/1e5:.3f}, "
          f"acceleration {p['acceleration']/1e5:.3f}, supports {p['supports']/1e5:.3f})")
    p = r["dP_tube_parts"]
    print(f"      Tube-side ΔP = {r['dP_tube']/1e5:.3f} bar irreversible (friction {p['friction']/1e5:.3f}, ends {p['ends']/1e5:.3f}); "
          f"net with downflow gravity {r['dP_tube_net']/1e5:.3f} bar")
    print(f"(v)   Unladen weight = {r['weight']/1e3:.0f} t  (tubes {w['tubes']/1e3:.0f}, shell {w['shell']/1e3:.0f}, heads {w['heads']/1e3:.0f}, "
          f"tubesheets {w['tubesheets']/1e3:.0f}, supports {w['supports']/1e3:.0f}, allowance {w['allowance']/1e3:.0f} t)")
    s = r["segments"]
    bounds = {}
    for z0, z1, reg in zip(s["z0"], s["z1"], s["regime"]):
        bounds.setdefault(reg, [z0, z1])[1] = z1
    print("Regions: " + "; ".join(f"{k} {v[0]:.2f}–{v[1]:.2f} m" for k, v in bounds.items()))
    print(f"Closure: primary at the top {r['report']['T_pri_top']:.2f} °C (target {sp['T_pri_in']:.0f}), "
          f"steam outlet {r['report']['T_sec_top']:.2f} °C (target {sp['T_steam_out']:.0f}), {len(s['z'])} segments")
    print(segment_table(r))


# %% [main]
if __name__ == "__main__":
    import sys
    P = float(sys.argv[1]) if len(sys.argv) > 1 else 70.0
    r = design(dict(SPEC_GIVEN, P_steam_bar=P))
    report(r)
