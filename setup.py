# Copyright (C) 2021 Ruben Vorderman
#
# This file is part of gzip_static.
#
# gzip_static is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gzip_static is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gzip_static.  If not, see <https://www.gnu.org/licenses/>.


from pathlib import Path

from setuptools import find_packages, setup

setup(
    name="gzip_static",
    version="0.1.0",
    description="Compress your static website with gzip for faster serving "
                "with NGiNX's gzip_static on.",
    author="Ruben Vorderman",
    author_email="rubenvorderman@gmail.com",  # A placeholder for now
    long_description=Path("README.rst").read_text(encoding='UTF-8'),
    long_description_content_type="text/x-rst",
    license="GPL-3.0-or-later",
    keywords="static html precompression gzip checksum",
    zip_safe=False,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={
        'gzip_static': ['extensions.txt']
    },
    url="https://github.com/rhpvorderman/gzip_static",
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: GNU General Public License v3 or later "
        "(GPLv3+)",
    ],
    python_requires=">=3.6",
    extras_require={
        "zopfli": ["zopfli"],
        "performance": ["xxhash>=2.0.0", "isal"],
        "full": ["zopfli", "xxhash>=2.0.0", "isal"]
    },
    entry_points={
        'console_scripts': ['gzip-static=gzip_static:main',
                            'gzip-static-find-orphans='
                            'gzip_static:find_orphans_main']
    }

)
