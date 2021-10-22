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
import argparse
import gzip
import hashlib
import io
import logging
import os
import zlib
from pathlib import Path
from typing import Generator, Set, Tuple

# Reading larger chunks of files makes it faster.
DEFAULT_BLOCK_SIZE = 32 * 1024
# Hashlib.sha1 is the fasted algorithm that is guaranteed to be in hashlib.
DEFAULT_HASH_ALGORITHM = hashlib.sha1
DEFAULT_COMPRESSION_LEVEL=9

# Precompress ending states
COMPRESSED = 0
RECOMPRESSED = 1
SKIPPED = 2

DEFAULT_EXTENSIONS_FILE = Path(__file__).parent / "extensions.txt"


def hash_file_contents(filepath: os.PathLike,
                       hash_algorithm=DEFAULT_HASH_ALGORITHM,
                       block_size:int = DEFAULT_BLOCK_SIZE):
    is_gzip = os.fspath(filepath).endswith(".gz")
    # Using a zlib decompressor has much less overhead than using GzipFile.
    # This comes with a memory overhead of compression_ratio * block_size.
    decompressor = zlib.decompressobj(wbits=31)
    if is_gzip:
        # Limit the block size when decompressing to limit memory overhead.
        # Worst-case scenario: only a single character is present. Tested on
        # a file with 100 million a's. Compressed with gzip -9: 97077
        # characters. With zopfli it was bigger.
        # Compression ratio is thus at maximum 100 million / 97077 ~= 1030.
        # Thus the maximum memory usage is the block_size * 1030. With
        # io.DEFAULT_BUFFER_SIZE that is about 8 mb. Which is acceptable:
        # edge cases will not crash the program with an out of memory error.
        # Repeating the test with only b"\xff", (so only binary ones) produced
        # a similar result.
        # NOTE: with gzip.open this is taken care of automatically because
        # the output of decompressor.decompress is limited in size.
        # This creates a lot of overhead though, and since we decompress only
        # small files this overhead is noticeable in the performance.
        block_size = io.DEFAULT_BUFFER_SIZE
    hasher = hash_algorithm()
    with open(filepath, "rb") as input_h:
        while True:
            block = input_h.read(block_size)
            if block == b"":
                return hasher.digest()
            if is_gzip:
                block = decompressor.decompress(block)
            hasher.update(block)


def compress_path(filepath: os.PathLike,
                  compresslevel: int = DEFAULT_COMPRESSION_LEVEL,
                  block_size: int = DEFAULT_BLOCK_SIZE):
    output_filepath = os.fspath(filepath) + ".gz"
    with open(filepath, mode="rb") as input_h:
        with gzip.open(output_filepath, mode="wb", compresslevel=compresslevel
                       ) as output_h:
            while True:
                block = input_h.read(block_size)
                if block == b"":
                    return
                output_h.write(block)


def precompress_file(filepath: os.PathLike,
                     compresslevel = DEFAULT_COMPRESSION_LEVEL,
                     hash_algorithm = DEFAULT_HASH_ALGORITHM,
                     force: bool = False) -> int:
    result = COMPRESSED
    gzipped_path = os.fspath(filepath) + ".gz"
    if os.path.exists(gzipped_path):
        result = RECOMPRESSED
        if not force:
            file_hash = hash_file_contents(filepath,
                                           hash_algorithm=hash_algorithm)
            gzipped_hash = hash_file_contents(gzipped_path,
                                              hash_algorithm=hash_algorithm)
            if file_hash == gzipped_hash:
                logging.debug(f"Skip {filepath}: already gzipped")
                return SKIPPED
            else:
                logging.debug(f"Hashes do not match for {filepath}: "
                              f"recompressing.")
    compress_path(filepath, compresslevel)
    return result


def find_static_files(dir: os.PathLike,
                      extensions: Set[str],
                      ) -> Generator[Path, None, None]:
    for path in Path(os.fspath(dir)).iterdir():
        if path.is_dir():
            yield from find_static_files(path, extensions)
        elif path.is_file() and path.suffix == ".gz":
            continue
        elif path.is_file() and path.suffix in extensions:
            yield path
        else:
            logging.debug(f"Skip {path}: unsupported extension")
        # TODO: Check if special behaviour is needed for symbolic links


def read_extensions_file(filepath: os.PathLike) -> Set[str]:
    with open(filepath, "rt") as input_h:
        return {line.strip() for line in input_h}


def gzip_static(dir: os.PathLike,
                extensions_file: os.PathLike = DEFAULT_EXTENSIONS_FILE,
                compresslevel: int = DEFAULT_COMPRESSION_LEVEL,
                hash_algorithm = DEFAULT_HASH_ALGORITHM,
                force: bool = False) -> Tuple[int, int, int]:
    results = [0, 0, 0]
    extensions = read_extensions_file(extensions_file)
    for static_file in find_static_files(dir, extensions):
        result = precompress_file(static_file, compresslevel,
                                  hash_algorithm, force)
        results[result] += 1
    return tuple(results)


def argument_parser() -> argparse.ArgumentParser():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=str,
                        help="The directory containing the static site")
    parser.add_argument("-l", "--compression-level",
                        choices=range(1, 10),
                        type=int,
                        default=DEFAULT_COMPRESSION_LEVEL,
                        help=f"The compression level that will be used for "
                             f"the gzip compression. "
                             f"Default: {DEFAULT_COMPRESSION_LEVEL}")
    parser.add_argument("-e", "--extensions-file", type=str,
                        default=DEFAULT_EXTENSIONS_FILE,
                        help="A file with extensions to consider when "
                             "compressing. Use one line per extension. "
                             "Check the default for an example.")
    parser.add_argument("-f", "--force", action="store_true",
                        help="Force recompression of all earlier compressed "
                             "files.")

    return parser


def main():
    args = argument_parser().parse_args()
    logging.basicConfig(level=logging.INFO)
    results = gzip_static(args.directory,
                          extensions_file=args.extensions_file,
                          compresslevel=args.compression_level,
                          force=args.force)
    print(f"New gzip files:     {results[COMPRESSED]}")
    print(f"Updated gzip files: {results[RECOMPRESSED]}")
    print(f"Skipped gzip files: {results[SKIPPED]}")
