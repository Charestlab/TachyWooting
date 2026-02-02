"""
Setup script for wooting-analog package.

This file is provided for backward compatibility and to enable
proper installation hooks when using `pip install .`

The actual package configuration is in pyproject.toml.
"""

from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop
import subprocess
import sys


class PostInstallCommand(install):
    """Post-installation hook for installation mode."""
    def run(self):
        install.run(self)
        # Run post-installation setup
        try:
            from wooting_package.post_install import run_post_install
            run_post_install()
        except Exception as e:
            print(f"Warning: Post-installation setup encountered an issue: {e}")
            print("You may need to run the setup manually.")


class PostDevelopCommand(develop):
    """Post-installation hook for development mode."""
    def run(self):
        develop.run(self)
        # Run post-installation setup
        try:
            from wooting_package.post_install import run_post_install
            run_post_install()
        except Exception as e:
            print(f"Warning: Post-installation setup encountered an issue: {e}")
            print("You may need to run the setup manually.")


# Use pyproject.toml for configuration, but add custom install commands
setup(
    cmdclass={
        'install': PostInstallCommand,
        'develop': PostDevelopCommand,
    },
)
