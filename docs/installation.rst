Installation
============

Core package
------------

Install the package from the repository root:

.. code-block:: bash

   pip install .

Visual TachyPy support
----------------------

Install optional TachyPy integration with:

.. code-block:: bash

   pip install ".[tachypy]"

Native interface
----------------

The native CFFI interface is built during normal package installation. If it is
missing, rebuild it explicitly:

.. code-block:: bash

   wooting-build-interface

If Python 3.12 reports that ``setuptools`` is missing, install it in the active
environment:

.. code-block:: bash

   python -m pip install "setuptools>=77.0"
