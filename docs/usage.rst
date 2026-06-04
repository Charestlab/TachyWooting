Usage
=====

Keyboard initialization
-----------------------

.. code-block:: python

   from wooting_package import WOOTING_ACQUISITION

   acq = WOOTING_ACQUISITION(
       threshold=0.8,
       min_pressure_start=0.33,
       max_pressure_start=0.66,
   )
   acq.initialize_keyboard(verbose=True)

Visual readiness feedback
-------------------------

.. code-block:: python

   acq.wait_keys_light_press_visual(
       screen=screen,
       response_handler=response_handler,
       target_keys=["z", "c"],
   )

Acquisition
-----------

.. code-block:: python

   data = acq.acquire_analog_values(target_keys=["z", "c"])

Logging
-------

.. code-block:: python

   acq.setup_logging(path="logs", name="participant_001", int_analog=2)
   acq.acquire_analog_values(target_keys=["z", "c"])
   acq.uninitialize_keyboard()
