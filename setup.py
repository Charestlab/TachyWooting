"""
Setup script for the Wooting keyboard interface.
"""
import os
from setuptools import setup, find_packages
from wooting_package.wooting_interface_builder import build_interface

# Compiler l'interface avant l'installation
build_interface()

# Obtenir le chemin du dossier du projet
project_dir = os.path.dirname(os.path.abspath(__file__))
readme_path = os.path.join(project_dir, 'README.md')

setup(
    name="wooting_interface",
    version="0.1.0",
    packages=find_packages(),
    package_data={
        'wooting_package': ['interface/*.so', 'interface/*.dylib', 'interface/*.dll', 'interface/*.pyd'],
    },
    install_requires=[
        "cffi>=1.15.0", 
        "pandas", 
        "pyarrow", 
        "numpy",
        "matplotlib" 
    ],
    author="Mathias Salvas-Hébert, Guillaume Lalonde-Beaudoin",
    description="Python interface for Wooting analog keyboards",
    long_description=open(readme_path).read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.6",
) 