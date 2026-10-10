"""Draws the README diagrams as PNG files in docs/.

GitHub clips text in Mermaid diagrams and shrinks wide ones, so the README
uses these images instead. Each figure is laid out top to bottom and about
1,500 pixels wide, so it stays readable at GitHub's page width.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

INK = "#1f2933"; GRAY = "#eef1f4"; EDGE = "#9aa5b1"; TEAL = "#0f766e"; TEAL_L = "#d5f0ec"
AMBER = "#b45309"; AMBER_L = "#fbebd5"; RED = "#b42318"; MUTED = "#52606d"
plt.rcParams["font.family"] = "DejaVu Sans"
os.makedirs("docs", exist_ok=True)


def box(ax, cx, cy, w, h, title, sub="", fill=GRAY, edge=EDGE, tsize=15, ssize=12):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                boxstyle="round,pad=0.02,rounding_size=0.15", fc=fill, ec=edge, lw=1.4))
    if sub:
        ax.text(cx, cy + h * 0.16, title, ha="center", va="center", fontsize=tsize, weight="bold", color=INK)
        ax.text(cx, cy - h * 0.20, sub, ha="center", va="center", fontsize=ssize, color=INK)
    else:
        ax.text(cx, cy, title, ha="center", va="center", fontsize=tsize, weight="bold", color=INK)


def arrow(ax, p1, p2, color=INK, ls="-", rad=0.0):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=18, color=color, lw=1.8,
                                 linestyle=ls, connectionstyle=f"arc3,rad={rad}"))


def save(fig, name):
    fig.savefig(os.path.join("docs", name), dpi=150, bbox_inches="tight", pad_inches=0.3, facecolor="white")
    plt.close(fig)


# 1. Translation loop, top to bottom
fig, ax = plt.subplots(figsize=(10.6, 12))
ax.set_xlim(0, 10.6); ax.set_ylim(0, 12); ax.axis("off")
ax.text(0.2, 11.6, "How a SAS program gets translated and checked", fontsize=18, weight="bold", color=INK)
C = 5.0
box(ax, C, 10.4, 4.6, 1.1, "SAS program", "the original, trusted code")
box(ax, C, 8.5, 4.6, 1.1, "Translator", "Claude Haiku writes PySpark", AMBER_L, AMBER)
box(ax, C, 6.6, 4.6, 1.1, "Runner", "runs the PySpark on practice data")
box(ax, C, 4.5, 4.6, 1.3, "Verifier", "plain Python: compares the\noutput with the answer key", TEAL_L, TEAL)
box(ax, 9.0, 4.5, 2.7, 1.3, "SAS answer key", "made by real SAS", tsize=13, ssize=11)
box(ax, C, 2.1, 4.6, 1.3, "Final check", "hidden copy of the data,\nrun once, never shown to Haiku", TEAL_L, TEAL)
box(ax, C, 0.45, 4.6, 0.8, "Translation accepted", fill="white", edge=TEAL, tsize=13)
arrow(ax, (C, 9.85), (C, 9.05))
arrow(ax, (C, 7.95), (C, 7.15))
arrow(ax, (C, 6.05), (C, 5.15))
arrow(ax, (7.65, 4.5), (7.3, 4.5))
arrow(ax, (C, 3.85), (C, 2.75), color=TEAL)
ax.text(C + 0.15, 3.3, "PASS", fontsize=13, weight="bold", color=TEAL)
arrow(ax, (C, 1.45), (C, 0.85), color=TEAL)
arrow(ax, (2.7, 4.5), (2.7, 8.5), color=RED, ls="--", rad=-0.2)
ax.text(0.1, 6.5, "FAIL:\nshort report,\nat most 5\nexample rows.\nUp to 5 tries.", fontsize=11.5, color=RED, va="center")
save(fig, "how-it-works.png")

# 2. Reviewer experiment, top to bottom
fig, ax = plt.subplots(figsize=(10, 8.2))
ax.set_xlim(0, 10); ax.set_ylim(0, 8.2); ax.axis("off")
ax.text(0.2, 7.8, "The AI reviewer experiment (separate from the loop)", fontsize=18, weight="bold", color=INK)
box(ax, 2.6, 6.6, 4.2, 1.1, "SAS program", "the original")
box(ax, 7.4, 6.6, 4.2, 1.1, "PySpark translation", "one graded attempt")
box(ax, 5.0, 4.6, 6.0, 1.2, "AI reviewer", "Claude Sonnet reads both, no data", AMBER_L, AMBER)
box(ax, 5.0, 2.7, 6.0, 1.1, "SAME or DIFFERENT", "same question asked 3 times")
box(ax, 5.0, 0.8, 6.0, 1.2, "Scored against the verifier", "which answers matched the proven result?", TEAL_L, TEAL)
arrow(ax, (2.6, 6.05), (4.0, 5.2))
arrow(ax, (7.4, 6.05), (6.0, 5.2))
arrow(ax, (5.0, 4.0), (5.0, 3.25))
arrow(ax, (5.0, 2.15), (5.0, 1.4))
save(fig, "reviewer-experiment.png")

# 3. Where each part runs, top to bottom
fig, ax = plt.subplots(figsize=(10, 11))
ax.set_xlim(0, 10); ax.set_ylim(0, 11); ax.axis("off")
ax.text(0.2, 10.6, "Where each part runs", fontsize=18, weight="bold", color=INK)

def zone(x, y, w, h, title, fill, edge):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.2",
                                fc=fill, ec=edge, lw=1.4, ls="--"))
    ax.text(x + 0.25, y + h - 0.35, title, fontsize=14, weight="bold", color=INK, va="center")

zone(0.3, 7.2, 9.4, 2.9, "SAS OnDemand for Academics (SAS's cloud)", GRAY, EDGE)
ax.text(0.6, 9.0, "Runs the ten SAS programs on the uploaded data", fontsize=12.5, color=INK)
ax.text(0.6, 8.4, "Writes each output table to lab/out", fontsize=12.5, color=INK)
ax.text(0.6, 7.8, "Gets invented data only", fontsize=12.5, color=MUTED)

zone(0.3, 2.9, 9.4, 3.4, "Your Mac", TEAL_L, TEAL)
ax.text(0.6, 5.3, "make_data.py builds the invented loan data", fontsize=12.5, color=INK)
ax.text(0.6, 4.7, "run_sas.py talks to SAS through SASPy", fontsize=12.5, color=INK)
ax.text(0.6, 4.1, "run_pyspark.py runs PySpark locally; verify.py compares", fontsize=12.5, color=INK)
ax.text(0.6, 3.5, "translate.py and judge.py call the AI models", fontsize=12.5, color=INK)

zone(0.3, 0.1, 9.4, 1.9, "Anthropic API", AMBER_L, AMBER)
ax.text(0.6, 1.1, "Claude Haiku (translator) and Claude Sonnet (reviewer)", fontsize=12.5, color=INK)
ax.text(0.6, 0.5, "Gets SAS code, PySpark code and short reports. Never the data.", fontsize=12.5, color=MUTED)

arrow(ax, (3.0, 6.3), (3.0, 7.2))
ax.text(3.15, 6.75, "upload data, send programs", fontsize=11.5, color=INK)
arrow(ax, (7.0, 7.2), (7.0, 6.3))
ax.text(7.15, 6.75, "answer keys", fontsize=11.5, color=INK)
arrow(ax, (3.0, 2.9), (3.0, 2.0))
ax.text(3.15, 2.45, "code and short reports", fontsize=11.5, color=INK)
arrow(ax, (7.0, 2.0), (7.0, 2.9))
ax.text(7.15, 2.45, "new code, verdicts", fontsize=11.5, color=INK)
save(fig, "where-it-runs.png")
print("ok")
