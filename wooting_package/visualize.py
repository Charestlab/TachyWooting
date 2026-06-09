#!/usr/bin/env python3
"""
visualize.py — viewer for Wooting HDF5 logs.

Data layout:
  /trials/<trial4>/keys/<key4>/values   # shape=(N, 3)
Columns: ["position", "time_to_threshold", "time_abs"]

Usage:
  wooting-visualize FILE.hdf5 --list
  wooting-visualize FILE.hdf5 --trial 1 --key 29
  wooting-visualize FILE.hdf5 --trial 1 --all-keys
  wooting-visualize FILE.hdf5
"""
import argparse
import sys
from typing import Optional

import h5py
import numpy as np

FIXED_COLUMNS = ["position", "time_to_threshold", "time_abs"]
_COLOR_SINGLE  = "#4C72B0"
_COLOR_THRESH  = "#C0392B"
_COLOR_TITLE   = "#1C1C2E"
_COLOR_LABEL   = "#3C3C4E"
_COLOR_TICK    = "#7C7C8E"
_COLOR_SPINE   = "#D0D0DD"
_COLOR_GRID    = "#E8E8F0"


def _pad4(x: int) -> str:
    return f"{int(x):04d}"


def _trials(f: h5py.File) -> list[str]:
    return sorted(f["trials"].keys()) if "trials" in f else []


def _keys_for(f: h5py.File, trial4: str) -> list[str]:
    g = f.get(f"/trials/{trial4}/keys")
    return sorted(g.keys()) if isinstance(g, h5py.Group) else []


def _key_label(key4: str) -> str:
    """Return 'A (4)' style label, or just '4' if no HID mapping exists."""
    try:
        from wooting_package.wooting_utils import convert_char_to_keycode
        names = convert_char_to_keycode(int(key4))
        if names and names[0]:
            return f"{names[0]} ({int(key4)})"
    except Exception:
        pass
    return str(int(key4))


def _load_threshold(f: h5py.File, trial4: str) -> Optional[float]:
    g = f.get(f"/trials/{trial4}")
    if not isinstance(g, h5py.Group):
        return None
    val = g.attrs.get("threshold")
    return float(val) if val is not None else None


def _load_xy(f: h5py.File, trial4: str, key4: str):
    """Return (pos, tth, tabs, dataset, cols) for a key."""
    path = f"/trials/{trial4}/keys/{key4}/values"
    if path not in f:
        raise KeyError(f"Missing dataset at {path}")
    ds = f[path]
    if not isinstance(ds, h5py.Dataset):
        raise TypeError(f"{path} is not a dataset")
    arr = np.asarray(ds[()])
    cols_attr = ds.attrs.get("columns")
    cols = ([c.decode() if isinstance(c, (bytes, np.bytes_)) else str(c) for c in cols_attr]
            if cols_attr is not None else FIXED_COLUMNS)
    i_pos, i_tth, i_abs = map(cols.index, ("position", "time_to_threshold", "time_abs"))
    return arr[:, i_pos], arr[:, i_tth], arr[:, i_abs], ds, cols


def _print_preview(ds: h5py.Dataset, cols: list, head_n: int) -> None:
    arr = np.asarray(ds[()])
    print(f"\n{ds.name} — shape={arr.shape}")
    for row in arr[:min(head_n, len(arr))]:
        print("  " + ", ".join(f"{c}={row[j]:.6f}" for j, c in enumerate(cols)))


def _check_matplotlib():
    try:
        __import__("matplotlib.pyplot")
    except ImportError as exc:
        raise RuntimeError(
            'matplotlib required. Install with: pip install "wooting-analog[visualize]"'
        ) from exc


def _make_figure(title: str):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_title(title, pad=14, fontsize=13, fontweight="semibold", color=_COLOR_TITLE)
    ax.set_xlabel("time to threshold  (s)", fontsize=10, labelpad=8, color=_COLOR_LABEL)
    ax.set_ylabel("position", fontsize=10, labelpad=8, color=_COLOR_LABEL)
    ax.tick_params(axis="both", labelsize=9, labelcolor=_COLOR_TICK, color=_COLOR_SPINE)
    ax.set_ylim(0, 1)
    ax.grid(True, axis="y", alpha=1.0, linewidth=0.6, color=_COLOR_GRID, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_edgecolor(_COLOR_SPINE)
    return fig, ax


def _finalize(
    fig, ax, all_tth, all_tabs, save_path: Optional[str],
    *, threshold: Optional[float] = None, legend: bool = False,
) -> None:
    import matplotlib.pyplot as plt
    if all_tth.size:
        rng = float(all_tth.max() - all_tth.min())
        pad = 0.02 * (rng if rng > 0 else 1.0)
        ax.set_xlim(float(all_tth.min()) - pad, float(all_tth.max()) + pad)

    if threshold is not None:
        ax.axhline(threshold, linestyle="--", color=_COLOR_THRESH,
                   linewidth=1.2, alpha=0.75, zorder=2)
        ax.annotate(
            f"threshold  {threshold:.2f}",
            xy=(1, threshold), xycoords=("axes fraction", "data"),
            xytext=(6, 0), textcoords="offset points",
            va="center", ha="left", clip_on=False,
            color=_COLOR_THRESH, fontsize=8.5, fontstyle="italic",
        )

    offset = float(np.median(all_tabs - all_tth)) if all_tth.size else 0.0
    secax = ax.secondary_xaxis(
        "top", functions=(lambda x: x + offset, lambda x: x - offset)
    )
    secax.set_xlabel("time abs  (s)", labelpad=8, fontsize=10, color=_COLOR_LABEL)
    secax.tick_params(labelsize=9, labelcolor=_COLOR_TICK, color=_COLOR_SPINE)

    if legend:
        ax.legend(
            title="Key", title_fontsize=9,
            framealpha=0.95, fontsize=9,
            markerscale=2, edgecolor=_COLOR_SPINE, fancybox=False,
        )

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
        print(f"Plot saved to {save_path}")
    else:
        plt.show()


def visualize(f: h5py.File, trial4: str, key4: str, head_n: int = 10, save_path: Optional[str] = None) -> None:
    _check_matplotlib()
    pos, tth, tabs, ds, cols = _load_xy(f, trial4, key4)
    _print_preview(ds, cols, head_n)
    fig, ax = _make_figure(f"Trial {int(trial4)}  ·  Key {_key_label(key4)}")
    ax.scatter(tth, pos, s=8, alpha=0.85, color=_COLOR_SINGLE, zorder=3)
    _finalize(fig, ax, tth, tabs, save_path, threshold=_load_threshold(f, trial4))


def visualize_all_keys(f: h5py.File, trial4: str, head_n: int = 10, save_path: Optional[str] = None) -> None:
    _check_matplotlib()
    keys = _keys_for(f, trial4)
    if not keys:
        print(f"No keys found for trial {trial4}.", file=sys.stderr)
        return

    import matplotlib.pyplot as plt
    colors = plt.cm.tab10.colors
    fig, ax = _make_figure(f"Trial {int(trial4)}  ·  {len(keys)} keys")

    all_tth, all_tabs = [], []
    for i, key4 in enumerate(keys):
        pos, tth, tabs, ds, cols = _load_xy(f, trial4, key4)
        _print_preview(ds, cols, head_n)
        all_tth.append(tth)
        all_tabs.append(tabs)
        ax.scatter(tth, pos, s=8, alpha=0.8,
                   color=colors[i % len(colors)], label=_key_label(key4), zorder=3)

    _finalize(fig, ax, np.concatenate(all_tth), np.concatenate(all_tabs), save_path,
              threshold=_load_threshold(f, trial4), legend=True)


def main():
    ap = argparse.ArgumentParser(description="Visualize Wooting HDF5 logs.")
    ap.add_argument("file", help="Path to .h5/.hdf5")
    ap.add_argument("--list", action="store_true", help="List trials and exit")
    ap.add_argument("--trial", type=int, help="Trial id (e.g. 1)")
    ap.add_argument("--key", type=int, help="Key id (e.g. 29)")
    ap.add_argument("--all-keys", action="store_true", help="Plot all keys of the trial on one figure")
    ap.add_argument("--n", type=int, default=10, help="Rows to preview (default 10)")
    ap.add_argument("--save", type=str, help="Save plot to file (e.g. plot.png)")
    args = ap.parse_args()

    try:
        f = h5py.File(args.file, "r")
    except Exception as e:
        sys.exit(f"Failed to open file: {e}")

    with f:
        if args.list:
            ts = _trials(f)
            print("Trials:" if ts else "No /trials group found.")
            for t in ts:
                print(" ", t)
            return

        if args.trial is None:
            ts = _trials(f)
            trial4 = _pad4(int(input(f"Pick trial ({', '.join(ts)}): ").strip()))
        else:
            trial4 = _pad4(args.trial)

        if args.all_keys:
            visualize_all_keys(f, trial4, head_n=args.n, save_path=args.save)
            return

        if args.key is None:
            ks = _keys_for(f, trial4)
            raw = input(f"Pick key ({', '.join(ks)}, all): ").strip().lower()
            if raw == "all":
                visualize_all_keys(f, trial4, head_n=args.n, save_path=args.save)
                return
            key4 = _pad4(int(raw))
        else:
            key4 = _pad4(args.key)

        visualize(f, trial4, key4, head_n=args.n, save_path=args.save)


if __name__ == "__main__":
    main()
