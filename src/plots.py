# %% [markdown]
# ## Figures
# Figures for the report (black and white).

# %%
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

K, G1, G2, BAND = "#000000", "#555555", "#9a9a9a", "#ececec"
S1 = dict(color=K, lw=1.8, ls="-")          # series 1: solid black
S2 = dict(color=K, lw=1.8, ls="--")         # series 2: dashed black
S3 = dict(color=G1, lw=1.8, ls=":")         # series 3: dotted grey
plt.rcParams.update({"font.size": 9, "font.family": "STIXGeneral", "axes.titlesize": 10, "axes.labelsize": 9,
                     "legend.fontsize": 8, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": K, "figure.dpi": 110, "mathtext.fontset": "stix"})


def _grid(ax):
    ax.grid(True, color="#d5d5d5", lw=0.5)
    ax.set_axisbelow(True)


def _save(fig, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


# ------------------------------------------------------------------ Q1
def q1_radial_profile(r, path, fuel_rod):
    rr, TT, t = fuel_rod.radial_profile(r["q_max"], r)
    rod = r["rod"]
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    r_p, r_co = rod["d_pellet"] / 2 * 1e3, rod["d_clad_out"] / 2 * 1e3
    ax.axvspan(r_p, r_co, color=BAND, lw=0)
    ax.plot(rr, TT, **S1)
    ax.axhline(rod["T_fuel_max"], color=G1, lw=1.0, ls="--")
    ax.text(0.15, rod["T_fuel_max"] + 25, "$T_{c,max}$ = 2000 °C", color=G1, fontsize=8)
    for rad, temp in [(0, t["T_centre"]), (r_p, t["T_fuel_surface"]), (r_co, t["T_clad_out"])]:
        ax.plot([rad], [temp], "o", color=K, ms=4)
    ax.plot([r_co, r_co + 0.6], [t["T_clad_out"], rod["T_bulk"]], color=K, lw=1.4, ls=":")
    ax.text(0.15, 1750, f"$T_c$ = {t['T_centre']:.0f} °C\n$T_s$ = $T_{{ci}}$ = {t['T_fuel_surface']:.0f} °C\n"
            f"$T_{{co}}$ = {t['T_clad_out']:.0f} °C\n$T_b$ = {rod['T_bulk']:.0f} °C", fontsize=8, va="top",
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=G2))
    ax.text(r_p / 2, 120, "UO$_2$ pellet", ha="center", fontsize=8, color=G1)
    ax.text((r_p + r_co) / 2, 120, "clad", ha="center", fontsize=8, color=G1)
    ax.set_xlabel("radius $r$ (mm)")
    ax.set_ylabel("temperature (°C)")
    ax.set_title(f"Radial temperature at $q'$ = {r['q_max']/1e3:.1f} kW/m")
    ax.set_ylim(0, 2200)
    _grid(ax)
    return _save(fig, path)


def q1_breakdown(r, rows, path, fuel_rod):
    t = fuel_rod.temperatures(r["q_max"], r)
    drops = [("coolant film", t["T_clad_out"] - t["T_bulk"]), ("cladding", t["T_clad_in"] - t["T_clad_out"]),
             ("pellet", t["T_centre"] - t["T_fuel_surface"])]
    fig, (a, b) = plt.subplots(1, 2, figsize=(9, 3.4), gridspec_kw=dict(width_ratios=[1, 1.3]))
    names = [d[0] for d in drops][::-1]; vals = [d[1] for d in drops][::-1]
    a.barh(names, vals, color="#bdbdbd", edgecolor=K, height=0.55)
    for i, v in enumerate(vals):
        a.text(v + 15, i, f"{v:.0f} K", va="center", fontsize=8)
    a.set_xlabel("temperature drop at $q'_{max}$ (K)")
    a.set_title("Temperature drop per layer")
    a.set_xlim(0, max(vals) * 1.25)
    _grid(a)
    names = [x[0] for x in rows][::-1]; vals = [x[1] / 1e3 for x in rows][::-1]
    b.barh(names, vals, color=["#555555" if "Base" in n else "#bdbdbd" for n in names], edgecolor=K, height=0.55)
    for i, v in enumerate(vals):
        b.text(v + 0.5, i, f"{v:.1f}", va="center", fontsize=8)
    b.set_xlabel("$q'_{max}$ (kW/m)")
    b.set_title("Sensitivity of $q'_{max}$")
    b.set_xlim(0, max(vals) * 1.2)
    _grid(b)
    fig.tight_layout()
    return _save(fig, path)


# ------------------------------------------------------------------ Q2
def q2_tq_diagram(pa_given, pa_adopted, path):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, pa, title in zip(axes, (pa_given, pa_adopted),
                             ("(a) as specified: 100 bar steam", f"(b) adopted: {pa_adopted['eb']['P_shell_in']:.0f} bar steam")):
        Qf = pa["Q"] / 1e6
        ax.plot(Qf, pa["T_pri"], label="primary (tube side)", **S1)
        ax.plot(Qf, pa["T_sec"], label="secondary (shell side)", **S2)
        bad = pa["dT"] < 0
        if bad.any():
            ax.fill_between(Qf, pa["T_pri"], pa["T_sec"], where=bad, facecolor="none", hatch="////", edgecolor=G2, lw=0)
            i = int(np.argmin(pa["dT"]))
            ax.annotate(f"temperature cross\n$\\Delta T_{{min}}$ = {pa['dT_min']:.1f} K", (Qf[i], pa["T_sec"][i]), xytext=(20, -45),
                        textcoords="offset points", fontsize=8, arrowprops=dict(arrowstyle="-", color=G1))
        else:
            ib = int(np.argmin(np.abs(pa["Q"] - pa["frac_boil"] * pa["eb"]["Q_sg"])))
            ax.annotate(f"pinch {pa['dT_boil']:.1f} K", (Qf[ib], pa["T_sec"][ib]), xytext=(15, -30), textcoords="offset points",
                        fontsize=8, arrowprops=dict(arrowstyle="-", color=G1))
            ax.annotate(f"{pa['dT_hot']:.0f} K", (Qf[-1], pa["T_sec"][-1]), xytext=(-28, -14), textcoords="offset points", fontsize=8)
        ax.set_xlabel("heat transferred from the cold end, $Q$ (MW)")
        ax.set_title(title)
        _grid(ax)
    axes[0].set_ylabel("temperature (°C)")
    axes[0].legend(loc="lower right", frameon=False)
    fig.tight_layout()
    return _save(fig, path)


def _regime_bands(ax, seg, L):
    bounds, prev = [], None
    for z0, reg in zip(seg["z0"], seg["regime"]):
        if reg != prev:
            bounds.append((z0, reg)); prev = reg
    for i, (z0, reg) in enumerate(bounds):
        z1 = bounds[i + 1][0] if i + 1 < len(bounds) else L
        if i % 2:
            ax.axvspan(z0, z1, color=BAND, lw=0, zorder=0)
        ax.text((z0 + z1) / 2, 0.98, reg.replace(" ", "\n"), transform=ax.get_xaxis_transform(), ha="center", va="top",
                fontsize=7, color=G1)


def q2_axial_profiles(res, path):
    seg, L = res["segments"], res["L_tube"]
    z = seg["z0"]
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True)
    a, b, c, d = axes.ravel()
    a.plot(z, seg["T_pri"], label="primary $T_p$", **S1)
    a.plot(z, seg["T_sec"], label="secondary $T_s$", **S2)
    a.plot(z, seg["T_wall_out"], label="tube outer wall $T_w$", **S3)
    a.set_ylabel("temperature (°C)"); a.legend(loc="lower right", frameon=False); a.set_title("(a) Temperatures")
    b.plot(z, seg["x"], **S1)
    b.set_ylabel("steam quality $x$ (–)"); b.set_title("(b) Quality"); b.set_ylim(-0.05, 1.08)
    c.semilogy(z, seg["h_i"], label="$h_i$ tube side", **S1)
    c.semilogy(z, seg["h_o"], label="$h_o$ shell side", **S2)
    c.semilogy(z, seg["U"], label="$U$ (outer area)", **S3)
    c.set_ylabel("W/m²K"); c.legend(loc="center right", frameon=False); c.set_title("(c) Heat-transfer coefficients")
    c.set_xlabel("height from the feedwater inlet, $z$ (m)")
    c.set_ylim(5e2, 1.5e5)
    d.plot(z, seg["q"] / 1e3, **S1)
    d.set_ylabel("heat flux $q''$ (kW/m²)"); d.set_title("(d) Local heat flux, outer surface"); d.set_xlabel("height from the feedwater inlet, $z$ (m)")
    for ax in (a, b, c, d):
        _regime_bands(ax, seg, L); _grid(ax); ax.set_xlim(0, L)
    fig.tight_layout()
    return _save(fig, path)


def q2_pressure_and_duty(res, path):
    seg, L, eb = res["segments"], res["L_tube"], res["eb"]
    z = seg["z0"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.5))
    a.plot(z, seg["P_sec"], **S1)
    a.set_ylabel("shell-side pressure (bar)"); a.set_xlabel("height $z$ (m)"); a.set_title("(a) Shell-side pressure")
    Qc = np.cumsum(seg["dQ"]) / 1e6
    b.plot(seg["z1"], Qc, **S1)
    b.axhline(eb["Q_sg"] / 1e6, color=G2, lw=0.8, ls="--")
    b.set_ylabel("cumulative duty $Q(z)$ (MW)"); b.set_xlabel("height $z$ (m)"); b.set_title("(b) Cumulative heat transferred")
    b.set_ylim(0, eb["Q_sg"] / 1e6 * 1.18)
    for ax in (a, b):
        _regime_bands(ax, seg, L); _grid(ax); ax.set_xlim(0, L)
    fig.tight_layout()
    return _save(fig, path)


def q2_design_space(trade, conv, chosen_V, path):
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(11, 3.3))
    V = [t["V"] for t in trade]
    a.plot(V, [t["L"] for t in trade], "-o", color=K, lw=1.8, ms=4)
    a.set_xlabel("tube-side velocity $V_t$ (m/s)"); a.set_ylabel("tube height $L$ (m)"); a.set_title("(a) Height")
    b.plot(V, [t["weight"] / 1e3 for t in trade], "-o", color=K, lw=1.8, ms=4)
    b.set_xlabel("tube-side velocity $V_t$ (m/s)"); b.set_ylabel("dry weight (t)"); b.set_title("(b) Weight")
    for ax in (a, b):
        ax.axvline(chosen_V, color=G1, lw=1, ls="--")
    a.text(chosen_V + 0.08, min(t["L"] for t in trade), "selected", color=G1, fontsize=8)
    n = [r["n"] for r in conv]
    c.plot(n, [r["L"] for r in conv], "-o", color=K, lw=1.8, ms=4)
    c.axhline(conv[0]["L_fine"], color=G1, lw=1, ls="--")
    c.text(n[0], conv[0]["L_fine"] + 0.02 * conv[0]["L_fine"], f"fine march, {conv[0]['L_fine']:.2f} m", color=G1, fontsize=8)
    c.set_xlabel("number of segments $N_{seg}$"); c.set_ylabel("tube height $L$ (m)"); c.set_title("(c) Discretisation")
    c.set_xscale("log", base=2); c.set_xticks(n); c.set_xticklabels([str(k) for k in n])
    Ls = [r["L"] for r in conv] + [conv[0]["L_fine"]]
    c.set_ylim(min(Ls) * 0.97, max(Ls) * 1.03)
    for ax in (a, b, c):
        _grid(ax)
    fig.tight_layout()
    return _save(fig, path)
