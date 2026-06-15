Logging
=======

TachyWooting's logging system records each acquisition trial to hierarchical
HDF5. It is designed for experiment data: every monitored key gets its full
pressure trajectory, timestamps are kept in both onset-relative and absolute
forms, and trial-level metadata records how the response was triggered.

Logging lifecycle
-----------------

Logging is opt-in and follows three steps:

#. Call :meth:`tachywooting.WOOTING_ACQUISITION.setup_logging` after
   :meth:`~tachywooting.WOOTING_ACQUISITION.initialize_keyboard`.
#. Run acquisition trials with either
   :meth:`~tachywooting.WOOTING_ACQUISITION.acquire_analog_values` or
   :meth:`~tachywooting.WOOTING_ACQUISITION.acquire_integer_values`.
#. Always call :meth:`~tachywooting.WOOTING_ACQUISITION.uninitialize_keyboard`
   at the end. This releases the SDK and merges per-trial shards into the final
   ``.hdf5`` file.

Use ``try`` / ``finally`` so the merge happens even if your experiment exits
early:

.. code-block:: python

   from tachywooting import WOOTING_ACQUISITION

   acq = WOOTING_ACQUISITION(threshold=0.8)
   acq.initialize_keyboard(verbose=True)
   acq.setup_logging(name="participant_001", path="logs", int_analog=2)

   try:
       for _ in range(20):
           acq.acquire_analog_values(target_keys=["Z", "C"])
   finally:
       acq.uninitialize_keyboard()

``setup_logging`` creates a staging directory named like
``<name>_trials_<run_id>/`` and each acquisition writes one trial shard there.
The final combined file is created during ``uninitialize_keyboard()``, usually
as ``<path>/<name>.hdf5``.

.. note::

   Trial shards make completed trials resilient to mid-experiment crashes: the
   data already written to disk remains in the staging directory. If the script
   exits before ``uninitialize_keyboard()``, the final combined file is not
   created automatically, so inspect the staging directory before deleting it.

Choosing the storage mode
-------------------------

``setup_logging(..., int_analog=...)`` selects the pressure format for the
whole logged session:

.. list-table::
   :header-rows: 1
   :widths: 15 30 55

   * - Value
     - Acquisition method
     - Stored pressure
   * - ``2``
     - ``acquire_analog_values``
     - Floating-point pressure in ``[0.0, 1.0]``.
   * - ``1``
     - ``acquire_integer_values``
     - Quantized integer pressure in ``[0, 255]``.

The mode is a guardrail: TachyWooting raises a ``ValueError`` if you enable
integer logging and call ``acquire_analog_values``, or enable analog logging and
call ``acquire_integer_values``. This prevents mixed units inside one session.

Output layout
-------------

The final HDF5 file has one top-level ``trials`` group. Trial and key names are
zero-padded so lexical order matches numeric order:

.. code-block:: text

   participant_001.hdf5
   └── trials
       ├── 0001
       │   ├── attrs: backend, threshold, threshold_time, threshold_key, ...
       │   └── keys
       │       ├── 0006
       │       │   └── values    # N x 3
       │       └── 0007
       │           └── values    # N x 3
       └── 0002
           └── keys

Each ``values`` dataset has three columns:

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Column
     - Meaning
   * - ``position``
     - Pressure value. Unit depends on ``int_analog``: either ``[0.0, 1.0]`` or
       ``[0, 255]``.
   * - ``time_from_onset``
     - Seconds relative to the trial onset reference. If ``trial_start_ns`` was
       supplied to acquisition, this is relative to that timestamp; otherwise it
       is relative to acquisition start.
   * - ``time_abs``
     - Absolute wall-clock timestamp in seconds since the Unix epoch.

The dataset also stores a ``columns`` attribute with these column names.

Trial metadata
--------------

Each trial group stores metadata as HDF5 attributes. These are preserved when
trial shards are merged into the final file and are returned under ``"_attrs"``
by :func:`tachywooting.load_trial`.

.. list-table::
   :header-rows: 1
   :widths: 24 18 58

   * - Attribute
     - Type
     - Meaning
   * - ``backend``
     - str
     - Readout backend used for the trial: ``"read_analog"`` or
       ``"read_full_buffer"``.
   * - ``threshold``
     - float
     - Actuation threshold in ``[0, 1]``.
   * - ``threshold_time``
     - float
     - Seconds from onset to the threshold crossing.
   * - ``threshold_key``
     - int
     - HID keycode of the first monitored key that crossed threshold.
   * - ``trial_start_perf_ns``
     - int
     - ``time.perf_counter_ns()`` reference used internally for onset alignment.
   * - ``trial_start_clock``
     - str
     - Clock domain supplied for ``trial_start_ns``: ``"perf"`` or ``"mono"``.

``threshold_time`` and ``threshold_key`` are absent if threshold was never
reached during the acquisition window.

Timing alignment
----------------

For stimulus-locked experiments, pass the stimulus onset timestamp to
``acquire_analog_values``. TachyWooting supports two clock domains:

- ``trial_start_clock="perf"`` for ``time.perf_counter_ns()`` timestamps.
- ``trial_start_clock="mono"`` for ``time.monotonic_ns()`` timestamps, such as
  onset times returned by some display libraries.

.. code-block:: python

   onset_ns = time.perf_counter_ns()
   trial = acq.acquire_analog_values(
       target_keys=["Z", "C"],
       trial_start_ns=onset_ns,
       trial_start_clock="perf",
   )

After this, each sample's ``time_from_onset`` is measured from ``onset_ns``.
The threshold-relative time for any sample is:

.. code-block:: python

   sample_time_from_threshold = sample_time_from_onset - trial_attrs["threshold_time"]

Reading logs back
-----------------

Reading HDF5 logs does not require a keyboard or the native Wooting SDK.

Load a single trial:

.. code-block:: python

   from tachywooting import load_trial

   trial = load_trial("logs/participant_001.hdf5", 1)
   attrs = trial["_attrs"]
   z_key = "0006"

   pressure = trial[z_key]["position"]
   t = trial[z_key]["time_from_onset"]
   print(attrs["threshold"], attrs.get("threshold_time"))

Convert one trial to a long-format pandas DataFrame:

.. code-block:: python

   from tachywooting import load_trial, trial_to_dataframe

   trial = load_trial("logs/participant_001.hdf5", 1)
   df = trial_to_dataframe(trial)
   print(df.head())

Load the full session as a DataFrame:

.. code-block:: python

   from tachywooting import load_session

   df = load_session("logs/participant_001.hdf5")
   by_trial = df.groupby("trial")["position"].max()

When ``include_attrs=True`` (the default), ``load_session`` repeats trial-level
metadata columns on each row. This makes filtering and grouping straightforward:

.. code-block:: python

   responses = df.dropna(subset=["threshold_key"])
   z_trials = responses[responses["threshold_key"] == 6]

Visualizing logs
----------------

The package also includes a small plotting CLI:

.. code-block:: bash

   wooting-visualize logs/participant_001.hdf5 --list
   wooting-visualize logs/participant_001.hdf5 --trial 1 --key 6

Best practices
--------------

- Call ``setup_logging`` once per participant/session, after keyboard
  initialization.
- Use one logging mode per session: analog ``int_analog=2`` for most analyses,
  integer ``int_analog=1`` only when your pipeline needs SDK-like integer units.
- Wrap the experiment in ``try`` / ``finally`` and call ``uninitialize_keyboard``
  in the ``finally`` block.
- Save the value of ``acq.output_paths["hdf5"]`` or print it at the end of the
  session so the output file is easy to find.
- Keep the staging directory if an experiment crashes before merging; it contains
  the completed trial shards.
