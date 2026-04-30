from setuptools import setup, find_packages
import os
import re

here = os.path.dirname(__file__)
with open(os.path.join(here, "src", "tkegexpat", "__init__.py")) as f:
    version = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', f.read()).group(1)

setup(
    name="tkegexpat-cli",
    version=version,
    description="TKEG Expat command-line interface",
    python_requires=">=3.9",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    entry_points={"console_scripts": ["tkegexpat = tkegexpat.cli:main"]},
)
