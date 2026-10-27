"""Flow chart of the Q2 calculation scheme (matplotlib)."""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = os.path.join("figures", "flowchart.png")
DEFAULT_OUT = (os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "figures", "flowchart.png")
              if "__file__" in globals() else OUT)

# (key, y, text, kind)  -- all boxes centred at x = 0.5 except the side box
BOXES = [
    ("in",   0.95, "Input data: plant power, primary and steam conditions,\ntube size, pitch, material", "io"),
    ("eb",   0.85, "Energy balance: Q per SG, primary flow, steam flow,\nfeed and steam enthalpies", "proc"),
    ("chk",  0.75, "Approach at start of boiling ≥ 10 K ?", "dec"),
    ("tube", 0.65, "Tube wall thickness (ASME), tube count from velocity,\nshell-side flow area and D_e", "proc"),
    ("seg",  0.55, "Segment i (start at the bottom, i = 1 … 40)", "loop"),
    ("loc",  0.44, "Local properties, flow regime, h_i, h_o,\nwall temperature, U, q''", "proc"),
    ("upd",  0.33, "ΔQ = q'' A Δz ;  update h_sec and h_pri ;\nΔp of the segment", "proc"),
    ("done", 0.23, "Steam outlet enthalpy reached ?", "dec"),
    ("post", 0.13, "Height L = Σ Δz ; shell diameter and thickness,\nheads, tubesheets ; total pressure drops ; weight", "proc"),
    ("out",  0.03, "Results (i) to (v)", "io"),
]
FILL = dict(io="#e0e0e0", proc="white", dec="white", loop="#f2f2f2")
W, H = 0.62, 0.07


def draw(path=OUT):
    fig, ax = plt.subplots(figsize=(7.0, 9.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.02, 1.0)
    ax.axis("off")
    pos = {}
    for key, y, text, kind in BOXES:
        w = 0.42 if kind == "dec" else W
        ax.add_patch(FancyBboxPatch((0.5 - w / 2, y - H / 2), w, H, boxstyle="round,pad=0.01", fc=FILL[kind], ec="black",
                                    lw=1.0, ls="--" if kind == "dec" else "-"))
        ax.text(0.5, y, text, ha="center", va="center", fontsize=9)
        pos[key] = (y, w)
    # side box for the "no" branch of the feasibility check
    ax.add_patch(FancyBboxPatch((0.78, 0.75 - H / 2), 0.21, H, boxstyle="round,pad=0.01", fc="white", ec="black", lw=1.0))
    ax.text(0.885, 0.75, "Lower the steam\npressure", ha="center", va="center", fontsize=9)
    keys = [b[0] for b in BOXES]
    for a, b in zip(keys[:-1], keys[1:]):
        ya, yb = pos[a][0], pos[b][0]
        ax.add_patch(FancyArrowPatch((0.5, ya - H / 2), (0.5, yb + H / 2), arrowstyle="-|>", mutation_scale=12, color="black", lw=1.0))
        if a in ("chk", "done"):
            ax.text(0.515, (ya + yb) / 2, "yes", fontsize=9, va="center")
    # chk: no -> side box -> back to energy balance
    ax.add_patch(FancyArrowPatch((0.5 + 0.21, 0.75), (0.78, 0.75), arrowstyle="-|>", mutation_scale=12, color="black", lw=1.0))
    ax.text(0.745, 0.76, "no", fontsize=9, ha="center", va="bottom")
    ax.plot([0.885, 0.885, 0.5 + W / 2 + 0.02], [0.75 + H / 2, 0.85, 0.85], color="black", lw=1.0, ls="--")
    ax.add_patch(FancyArrowPatch((0.5 + W / 2 + 0.02, 0.85), (0.5 + W / 2, 0.85), arrowstyle="-|>", mutation_scale=12, color="black", lw=1.0))
    # done: no -> next segment
    ax.plot([0.5 - 0.21, 0.08, 0.08, 0.5 - W / 2 - 0.02], [0.23, 0.23, 0.55, 0.55], color="black", lw=1.0, ls="--")
    ax.add_patch(FancyArrowPatch((0.5 - W / 2 - 0.02, 0.55), (0.5 - W / 2, 0.55), arrowstyle="-|>", mutation_scale=12, color="black", lw=1.0))
    ax.text(0.07, 0.39, "no: next segment", fontsize=9, rotation=90, ha="center", va="center")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


if __name__ == "__main__":
    print(draw(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT))
