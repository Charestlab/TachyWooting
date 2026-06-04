Console Scripts
===============

This package installs the following command-line scripts.

``wooting-demo``
----------------

Entry point:

.. code-block:: toml

   wooting-demo = "wooting_package.cli:main"

Runs a terminal demo for reading analog pressure from a selected key.

Typical use:

.. code-block:: bash

   wooting-demo --key A --threshold 50

Use this to quickly verify that the keyboard, native interface, and pressure
readout are working.

``wooting-build-interface``
---------------------------

Entry point:

.. code-block:: toml

   wooting-build-interface = "wooting_package.post_install:run_post_install"

Runs post-install setup:

- Applies platform-specific permissions when needed.
- Builds the CFFI native interface.
- Applies macOS Gatekeeper fixes for bundled ``.dylib`` files.

Typical use:

.. code-block:: bash

   wooting-build-interface

Use this after installation if importing the package reports that the native
interface is missing.

``wooting-delete-interface``
----------------------------

Entry point:

.. code-block:: toml

   wooting-delete-interface = "wooting_package.wooting_utils:delete_interface"

Deletes generated CFFI interface artifacts and common cache files.

Typical use:

.. code-block:: bash

   wooting-delete-interface
   wooting-build-interface

Use this when you want to force a clean rebuild of the native interface.

``wooting-visual-fixation-demo``
--------------------------------

Entry point:

.. code-block:: toml

   wooting-visual-fixation-demo = "wooting_package.visual_fixation_demo:main"

Runs the TachyPy visual readiness demo with the interactive fixation cross.

Default behavior:

- Uses ``z`` as the left key and ``c`` as the right key.
- Shows real-time pressure feedback.
- Tracks hits, elapsed time, and efficiency.
- Flashes the background green after a successful hit.
- Waits for keys to be released before counting another hit.
- Exits with ``Escape``, ``Enter``, ``Space``, or ``q``.

Typical use:

.. code-block:: bash

   wooting-visual-fixation-demo

Install TachyPy support first:

.. code-block:: bash

   python -m pip install ".[tachypy]"

Useful options:

.. code-block:: bash

   wooting-visual-fixation-demo \
     --left-key z \
     --right-key c \
     --min-pressure 0.33 \
     --max-pressure 0.66 \
     --hold-seconds 0.30

``wooting-mini-bw-experiment``
------------------------------

Entry point:

.. code-block:: toml

   wooting-mini-bw-experiment = "wooting_package.mini_bw_experiment:main"

Runs a no-file TachyPy mini-experiment for testing response trials and
finger-removal tracking.

Default behavior:

- Generates black and white image stimuli from ``np.zeros(...)`` and
  ``np.ones(...)``.
- Uses ``z`` as the yes response and ``c`` as the no response.
- Asks whether the image is white.
- Uses visual light-press readiness before each trial.
- Tracks finger-removal trials in memory only.
- Flags the participant when finger removals occur for 2 consecutive trials.
- Exits with ``Escape``, ``Enter``, ``Space``, or ``q``.

Typical use:

.. code-block:: bash

   wooting-mini-bw-experiment

Useful options:

.. code-block:: bash

   wooting-mini-bw-experiment \
     --trials 30 \
     --yes-key z \
     --no-key c \
     --min-pressure 0.33 \
     --max-pressure 0.66 \
     --removal-streak-limit 2

Markdown Source
---------------

The Markdown source for this page is also available at ``docs/scripts.md``.
