#!/usr/bin/env python3
"""
visualize.py — quick viewer for hierarchical Wooting HDF5 logs.

Data layout (fixed):
  /trials/<trial4>/keys/<key4>/values   # shape=(N, 3)
Columns (fixed order unless HDF5 attribute overrides):
  ["position", "time_to_threshold", "time_abs"]

Usage:
  python3 visualize.py FILE.hdf5 --list
  python3 visualize.py FILE.hdf5 --trial 1 --key 29
  python3 visualize.py FILE.hdf5                # prompts for trial/key

The plot shows:
  - Y: position
  - X (bottom): time_to_threshold
  - X (top): time_abs (affine transform of bottom axis)
"""
import argparse
import sys
from typing import Optional

import h5py
import numpy as np

FIXED_COLUMNS = ["position", "time_to_threshold", "time_abs"]

def _pad4(x: int) -> str:
    return f"{int(x):04d}"

def _trials(f: h5py.File) -> list[str]:
    return sorted(f["trials"].keys()) if "trials" in f else []

def _keys_for(f: h5py.File, trial4: str) -> list[str]:
    g = f.get(f"/trials/{trial4}/keys")
    return sorted(g.keys()) if isinstance(g, h5py.Group) else []

def _load_values(f: h5py.File, trial4: str, key4: str) -> h5py.Dataset:
    path = f"/trials/{trial4}/keys/{key4}/values"
    if path not in f:
        raise KeyError(f"Missing dataset at {path}")
    ds = f[path]
    if not isinstance(ds, h5py.Dataset):
        raise TypeError(f"{path} is not a dataset")
    return ds

def visualize(ds: h5py.Dataset, head_n: int = 10, save_path: Optional[str] = None) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            'matplotlib is required for plotting. Install it with: pip install "wooting-analog[visualize]"'
        ) from exc

    arr = np.asarray(ds[()])                      # (N, 3)
    cols_attr = ds.attrs.get("columns")
    cols = [c.decode() if isinstance(c, (bytes, np.bytes_)) else str(c)
            for c in cols_attr] if cols_attr is not None else FIXED_COLUMNS
    i_pos, i_tth, i_abs = map(cols.index, ("position", "time_to_threshold", "time_abs"))

    pos, tth, tabs = arr[:, i_pos], arr[:, i_tth], arr[:, i_abs]
    print(f"\n{ds.name} — shape={arr.shape}, columns={cols}")
    for row in arr[: min(head_n, len(arr))]:
        print("  " + ", ".join(f"{c}={row[j]:.6f}" for j, c in enumerate(cols)))

    # top x-axis (time_abs) is an affine transform of bottom x-axis (time_to_threshold)
    offset = float(np.median(tabs - tth)) if len(arr) else 0.0
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.scatter(tth, pos, s=6, alpha=0.85)
    ax.set_xlabel("time_to_threshold (s)")
    ax.set_ylabel("position")
    ax.set_title(f"{ds.name} — position vs time_to_threshold\n"
                 f"top axis = time_abs (offset≈{offset:.6f}s)")
    ax.grid(True, alpha=0.3)

    def fwd(x): return x + offset     # tth -> tabs
    def inv(x): return x - offset     # tabs -> tth
    ax.secondary_xaxis("top", functions=(fwd, inv)).set_xlabel("time_abs (s)")

    if len(tth):
        xmin, xmax = float(tth.min()), float(tth.max())
        pad = 0.02 * (xmax - xmin if xmax > xmin else 1.0)
        ax.set_xlim(xmin - pad, xmax + pad)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path)
        print(f"Plot saved to {save_path}")
    else:
        plt.show()

def main():
    ap = argparse.ArgumentParser(description="Visualize /trials/<trial>/keys/<key>/values from an HDF5 file.")
    ap.add_argument("file", help="Path to .h5/.hdf5")
    ap.add_argument("--list", action="store_true", help="List trials and exit")
    ap.add_argument("--trial", type=int, help="Trial id (e.g., 1)")
    ap.add_argument("--key", type=int, help="Key id (e.g., 29)")
    ap.add_argument("--n", type=int, default=10, help="Rows to preview (default 10)")
    ap.add_argument("--save", type=str, help="Save plot to file (e.g., plot.png)")
    args = ap.parse_args()

    try:
        f = h5py.File(args.file, "r")
    except Exception as e:
        print("Failed to open file:", e, file=sys.stderr)
        sys.exit(2)

    with f:
        if args.list:
            ts = _trials(f)
            print("Trials:" if ts else "No /trials group found.")
            for t in ts:
                print(" ", t)
            return

        trial4 = _pad4(args.trial) if args.trial is not None else (
            (lambda ts: _pad4(int(input(f"Pick trial {ts} or number: ").strip())))
            (", ".join(_trials(f)) or "(none)")
        )
        if args.trial is None and trial4 not in f.get("trials", {}):
            # user typed number; reformat to 4 digits
            if "trials" in f and trial4 not in f["trials"]:
                print(f"Trial {trial4} not found.", file=sys.stderr)
                return

        key4 = _pad4(args.key) if args.key is not None else (
            (lambda ks: _pad4(int(input(f"Pick key {', '.join(ks)} or number: ").strip())))
            (_keys_for(f, trial4))
        )
        if args.key is None and key4 not in f.get(f"/trials/{trial4}/keys", {}):
            g = f.get(f"/trials/{trial4}/keys")
            if not (isinstance(g, h5py.Group) and key4 in g):
                print(f"Key {key4} not found for trial {trial4}.", file=sys.stderr)
                return

        visualize(_load_values(f, trial4, key4), head_n=args.n, save_path=args.save)

if __name__ == "__main__":
    main()
