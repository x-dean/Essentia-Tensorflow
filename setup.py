#!/usr/bin/env python3
"""
Setup script for Playlist App CLI
"""

from setuptools import setup, find_packages

# Long description
long_description = "Playlist App - Audio discovery and playlist generation with Essentia and TensorFlow"

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="playlist-app",
    version="0.1.0",
    author="Playlist App Team",
    description="A playlist generation app with audio analysis using Essentia and TensorFlow",
    long_description="Playlist App - Audio discovery and playlist generation with Essentia and TensorFlow",
    long_description_content_type="text/plain",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "playlist=scripts.playlist_cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
