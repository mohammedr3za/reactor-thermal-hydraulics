#!/usr/bin/env python3
"""Generate the two notebooks in notebooks/ from the modules. Run after any change to fuel_rod.py,
sg_design.py, plots.py or flowchart.py:

    python3 src/make_notebooks.py

The modules are split into cells at `# %%` markers (`# %% [markdown]` = markdown cell,
`# %% [main]` = skipped). The notebooks are written WITHOUT outputs; every source line ends
with a newline so they survive the Drive API. Do not edit the .ipynb files by hand.
"""
import os
import re

import nbformat

HERE = os.path.dirname(os.path.abspath(__file__))
NB_DIR = os.path.join(os.path.dirname(HERE), "notebooks")


def cells_from_module(path, tag=None):
    text = open(os.path.join(HERE, path), encoding="utf-8").read()
    parts = re.split(r"^# %%(.*)$", text, flags=re.M)
    cells = []
    for marker, body in zip(parts[1::2], parts[2::2]):
        body = body.strip("\n")
        if "[main]" in marker:
            continue
        if "[markdown]" in marker:
            md = "\n".join(l[2:] if l.startswith("# ") else l.lstrip("#") for l in body.splitlines())
            cells.append(("markdown", md, tag))
        elif body:
            cells.append(("code", body, tag))
    return cells


def whole_file_cell(path, tag=None, drop_main=True):
    text = open(os.path.join(HERE, path), encoding="utf-8").read()
    if drop_main and 'if __name__ == "__main__":' in text:
        text = text[:text.index('if __name__ == "__main__":')].rstrip("\n")
    return [("code", text, tag)]


INSTALL = ("code", '''# steam tables (IAPWS-IF97); install once in Colab
try:
    import iapws
except ImportError:
    %pip install -q iapws
import os
os.makedirs("figures", exist_ok=True)
FIG = "figures"''')

HEADER = (
    "# Reactor thermal hydraulics\n\n"
)

Q1_RUN = [
    ("markdown", "## Results"),
    ("code", "r = report()"),
    ("markdown", "### Figures", "plot"),
    ("code", '''from IPython.display import Image, display
display(Image(q1_radial_profile(r, f"{FIG}/Q1_radial_profile.png", __import__(__name__))))
display(Image(q1_breakdown(r, sensitivities(r), f"{FIG}/Q1_breakdown.png", __import__(__name__))))''', "plot"),
    ("markdown", '''## Result
The pellet-centre limit sets the permissible linear heat rate: $q'_{max}$ = 55.4 kW/m for the rod
as set (no gap). The clad limit is 668 kW/m and does not apply. A gap conductance of
5000–10 000 W/m²K reduces $q'_{max}$ to 41–47 kW/m.'''),
]

Q2_RUN = [
    ("markdown", '''## 1. Feasibility of the specification
At 100 bar the steam saturates at 311 °C. The primary leaves at 295 °C. The T–Q diagram shows a
temperature cross. The design uses 70 bar and keeps all other values.'''),
    ("code", '''alts, P_max = alternatives(SPEC_GIVEN)
print(f"largest steam pressure with a 10 K approach at the onset of boiling: {P_max:.1f} bar")
for a in alts:
    print(f"{a['name']:50s} P = {a['P']:5.0f} bar, T_sat = {a['Tsat']:5.1f} °C, primary {a['T_in']:.0f}/{a['T_out']:.0f} °C, "
          f"min approach {a['dT_min']:6.1f} K at {100*a['frac']:3.0f} % of duty, m_pri = {a['m_pri']:.0f} kg/s")
SPEC = dict(SPEC_GIVEN, P_steam_bar=70.0)
pa_given, pa_adopted = pinch_analysis(SPEC_GIVEN), pinch_analysis(SPEC)
from IPython.display import Image, display
display(Image(q2_tq_diagram(pa_given, pa_adopted, f"{FIG}/Q2_TQ_diagram.png")))'''),
    ("markdown", "## 2. Design: segment-by-segment march, 40 segments"),
    ("code", '''res = design(SPEC, DESIGN)
report(res)'''),
    ("markdown", "### Axial profiles", "plot"),
    ("code", '''display(Image(q2_axial_profiles(res, f"{FIG}/Q2_axial_profiles.png")))
display(Image(q2_pressure_and_duty(res, f"{FIG}/Q2_pressure_duty.png")))''', "plot"),
    ("markdown", '''## 3. Design space and discretisation check
The tube-side velocity sets the tube count. The height follows. The sweep supports the selected
3.5 m/s. The segment-count check shows that the 40-segment result is converged.'''),
    ("code", '''trade = tradeoff(SPEC, V_list=(2.5, 3.0, 3.5, 4.0, 5.0, 6.0))
print("V[m/s]  N_tubes   L[m]  D_shell[m]  dP_tube[bar]  dP_shell[bar]  weight[t]")
for t in trade:
    print(f"{t['V']:5.1f}  {t['N']:8d}  {t['L']:6.2f}  {t['D_shell']:8.2f}  {t['dP_tube']/1e5:10.3f}  {t['dP_shell']/1e5:11.3f}  {t['weight']/1e3:8.0f}")
conv = convergence(SPEC, ns=(20, 40, 80))
print("segments  L[m]   fine L[m]  T_pri,top  T_steam,out")
for c in conv:
    print(f"{c['n']:8d}  {c['L']:6.3f}  {c['L_fine']:8.3f}  {c['T_pri_top']:8.2f}  {c['T_sec_top']:8.2f}")
display(Image(q2_design_space(trade, conv, DESIGN["V_tube"], f"{FIG}/Q2_design_space.png")))'''),
    ("markdown", "## 4. Flow chart of the calculation scheme", "plot"),
    ("code", '''display(Image(draw(f"{FIG}/flowchart.png")))''', "plot"),
]


def build(title_md, module_cells, run_cells, out):
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    cells = [("markdown", HEADER + title_md, None), INSTALL + (None,)] + module_cells + [c if len(c) == 3 else c + (None,) for c in run_cells]
    for kind, src, tag in cells:
        src = src.rstrip("\n") + "\n"
        cell = nbformat.v4.new_markdown_cell(src) if kind == "markdown" else nbformat.v4.new_code_cell(src)
        if tag:
            cell.metadata["tags"] = [tag]
        nb.cells.append(cell)
    nbformat.write(nb, out)
    return out


def main():
    q1 = cells_from_module("fuel_rod.py") + cells_from_module("plots.py", tag="plot")
    q2 = cells_from_module("sg_design.py") + cells_from_module("plots.py", tag="plot") + \
        [("markdown", "## Flow chart", "plot")] + whole_file_cell("flowchart.py", tag="plot")
    print(build("## Question 1: maximum permissible linear heat rate (analytical)", q1, Q1_RUN, os.path.join(NB_DIR, "Q1_fuel_rod_heat_rate.ipynb")))
    print(build("## Question 2: once-through steam generator design (code)", q2, Q2_RUN, os.path.join(NB_DIR, "Q2_once_through_steam_generator.ipynb")))


if __name__ == "__main__":
    main()
