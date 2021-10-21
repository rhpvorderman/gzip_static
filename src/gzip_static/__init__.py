# Copyright (C) 2021 Ruben Vorderman
# This file is part of gzip_static
#
# gzip_static is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# gzip_static is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with gzip_static.  If not, see <https://www.gnu.org/licenses/

"""Functions to compress a website's static files."""

import gzip
import hashlib
import os
from pathlib import Path
from typing import Generator, Set

# Reading larger chunks of files makes it faster.
DEFAULT_BLOCK_SIZE = 32 * 1024
# Hashlib.sha1 is the fasted algorithm that is guaranteed to be in hashlib.
DEFAULT_HASH_ALGORITHM = hashlib.sha1
DEFAULT_COMPRESSION_LEVEL=9

# Precompress ending states
COMPRESSED = 1
RECOMPRESSED = 2
SKIPPED = 3

DEFAULT_EXTENSIONS_FILE = Path(__file__).parent / "extensions.txt"


def hash_file_contents(filepath: os.PathLike,
                       algorithm=DEFAULT_HASH_ALGORITHM,
                       block_size:int = DEFAULT_BLOCK_SIZE):
    if os.fspath(filepath).endswith(".gz"):
        open_method = gzip.open
    else:
        open_method = open
    hasher = algorithm()
    with open_method(filepath, "rb") as input_h:
        while True:
            block = input_h.read(block_size)
            if block == b"":
                return hasher.digest()
            hasher.update(block)


def compress_path(filepath: os.PathLike,
                  compresslevel: int = DEFAULT_COMPRESSION_LEVEL,
                  block_size: int = DEFAULT_BLOCK_SIZE):
    output_filepath = os.fspath(filepath) + ".gz"
    with open(filepath, mode="rb") as input_h:
        with gzip.open(output_filepath, mode="wb", compresslevel=compresslevel
                       ) as output_h:
            output_h.write(input_h.read(block_size))


def precompress_file(filepath: os.PathLike,
                     compresslevel = DEFAULT_COMPRESSION_LEVEL,
                     force: bool = False) -> int:
    result = COMPRESSED
    gzipped_path = os.fspath(filepath) + ".gz"
    if os.path.exists(gzipped_path):
        if (not force and hash_file_contents(filepath) ==
                hash_file_contents(gzipped_path)):
            return SKIPPED
        else:
            result = RECOMPRESSED
    compress_path(filepath, compresslevel)
    return result


def find_static_files(dir: os.PathLike,
                      extensions: Set[str],
                      ) -> Generator[Path, None, None]:
    for path in Path(os.fspath(dir)).iterdir():
        if path.is_dir():
            yield from find_static_files(path, extensions)
        elif path.is_file() and path.suffix in extensions:
            yield path
        # TODO: Check if special behaviour is needed for symbolic links


def read_extensions_file(filepath: os.PathLike) -> Set[str]:
    with open(filepath, "rt") as input_h:
        return {line.strip() for line in input_h}

