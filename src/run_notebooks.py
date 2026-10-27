#!/usr/bin/env python3
"""Execute the notebooks headless and save the executed copies (with outputs) to results/.
Figures are written to results/figures. Usage: python3 src/run_notebooks.py [1 2]"""
import os
import sys
import time

import nbformat
from nbclient import NotebookClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results")
NOTEBOOKS = {1: "Q1_fuel_rod_heat_rate.ipynb", 2: "Q2_once_through_steam_generator.ipynb"}


def run_one(q):
    nb = nbformat.read(os.path.join(ROOT, "notebooks", NOTEBOOKS[q]), as_version=4)
    t = time.time()
    NotebookClient(nb, timeout=-1, kernel_name="python3", resources={"metadata": {"path": OUT}}).execute()
    dst = os.path.join(OUT, NOTEBOOKS[q])
    nbformat.write(nb, dst)
    print(f"Q{q}: executed in {time.time() - t:.0f} s -> {dst}")


if __name__ == "__main__":
    os.makedirs(os.path.join(OUT, "figures"), exist_ok=True)
    for q in [int(a) for a in sys.argv[1:]] or list(NOTEBOOKS):
        run_one(q)
