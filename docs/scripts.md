# Console Scripts

This package installs the following command-line scripts.

## `wooting-demo`

Entry point:

```toml
wooting-demo = "tachywooting.demos.cli:main"
```

Runs a terminal demo for reading analog pressure from a selected key.

![Wooting terminal demo](../repo_visuals/gifs/wooting-demo.gif)

Typical use:

```bash
wooting-demo --key A --threshold 50
```

Use this to quickly verify that the keyboard, native interface, and pressure readout are working.

## `wooting-build-interface`

Entry point:

```toml
wooting-build-interface = "tachywooting.post_install:run_post_install"
```

Runs post-install setup:

- Applies platform-specific permissions when needed.
- Builds the CFFI native interface.
- Applies macOS Gatekeeper fixes for bundled `.dylib` files.

Typical use:

```bash
wooting-build-interface
```

Use this after installation if importing the package reports that the native interface is missing.

## `wooting-delete-interface`

Entry point:

```toml
wooting-delete-interface = "tachywooting.wooting_utils:delete_interface"
```

Deletes generated CFFI interface artifacts and common cache files.

Typical use:

```bash
wooting-delete-interface
wooting-build-interface
```

Use this when you want to force a clean rebuild of the native interface.

## `wooting-visualize`

Entry point:

```toml
wooting-visualize = "tachywooting.visualize:main"
```

Plots logged analog pressure traces from an HDF5 session file (matplotlib).

## Visual demos (TachyPy)

The interactive fixation-cross demo and the mini black/white experiment now ship
with **TachyPy** — they require a display and the visual feedback engine, so they
are not part of this hardware package. Install `tachypy[wooting]` to get them:

```bash
pip install 'tachypy[wooting]'
tachypy-wooting-fixation-demo
tachypy-wooting-mini-bw
```
