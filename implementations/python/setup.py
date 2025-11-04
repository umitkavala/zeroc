"""
Zeroc Python implementation setup.
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="umitkavala-zeroc",
    version="1.0.0",
    description="Zeroc: High-Performance API Compression Protocol",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Zeroc Contributors",
    url="https://github.com/umitkavala/zeroc",
    packages=find_packages(exclude=["tests", "examples"]),
    python_requires=">=3.8",
    install_requires=[
        "zstandard>=0.21.0",
        "crc32c>=2.3",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pyright>=1.1.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Archiving :: Compression",
    ],
    keywords="compression protobuf zstd api performance",
)
