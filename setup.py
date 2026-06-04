from setuptools import setup


setup(
    cffi_modules=["wooting_package/wooting_interface_builder.py:ffibuilder"],
)
