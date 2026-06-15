TachyPy Integration
===================

TachyWooting is the hardware package: it handles Wooting keyboard setup,
pressure acquisition, readiness checks, and HDF5 logging. TachyPy is the
experiment/display package. When your experiment needs on-screen pressure
feedback, we highly recommend installing the integration through TachyPy:

- TachyPy GitHub: https://github.com/Charestlab/tachypy/
- TachyPy on PyPI: https://pypi.org/project/tachypy/
- TachyPy documentation: https://tachypy.readthedocs.io/

.. code-block:: bash

   pip install "tachypy[wooting]"

This exposes an enriched keyboard class directly from TachyPy:

.. code-block:: python

   from tachypy import WOOTING_ACQUISITION  # keyboard + visual feedback

That route adds ``wait_light_press_visual`` and keeps the visual feedback loop
inside TachyPy, where the screen, drawing, and response handling already live.
The hardware/logging behavior is still provided by TachyWooting underneath.

When to use which import
------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Use
     - When
   * - ``from tachypy import WOOTING_ACQUISITION``
     - You want TachyPy visual pressure feedback, especially
       ``wait_light_press_visual``.
   * - ``from tachywooting import WOOTING_ACQUISITION``
     - You want the hardware package directly: acquisition, readiness checks,
       and logging without TachyPy's visual feedback mixin.

The direct TachyWooting route can still be used inside a TachyPy experiment.
TachyPy can handle stimulus presentation while TachyWooting handles keyboard
readiness, acquisition, and logging.

Direct TachyWooting in a TachyPy experiment
-------------------------------------------

For most TachyPy experiments that need on-screen pressure feedback, prefer the
TachyPy integration above. If you only need TachyPy for stimulus presentation
and want to use TachyWooting directly for keyboard readiness, acquisition, and
logging, see the direct-import example in :ref:`usage_tachypy_direct_example`.

Visual demos
------------

The interactive fixation-cross demo and the mini black/white experiment ship
with TachyPy because they require a display and the visual feedback engine:

.. code-block:: bash

   pip install "tachypy[wooting]"
   tachypy-wooting-fixation-demo
   tachypy-wooting-mini-bw
