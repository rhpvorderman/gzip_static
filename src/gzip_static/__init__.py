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
import warnings
import zlib
from pathlib import Path
from typing import Generator, Set, Tuple, Union

# Accepted by open functions
Filepath = Union[str, os.PathLike]

# Reading larger chunks of files makes it faster.
DEFAULT_BLOCK_SIZE = 32 * 1024
# Hashlib.sha1 is the fasted algorithm that is guaranteed to be in hashlib.
DEFAULT_HASH_ALGORITHM = hashlib.sha1
DEFAULT_COMPRESSION_LEVEL = 9

# Compress_file_if_changed ending states
COMPRESSED = 0
RECOMPRESSED = 1
SKIPPED = 2

DEFAULT_EXTENSIONS_FILE = Path(__file__).parent / "extensions.txt"

# Limit CLI compresslevels to 6 and 9 to keep CLI clean.
AVAILABLE_COMPRESSION_LEVELS = [6, 9]

try:
    from zopfli import gzip as zopfli_gzip  # type: ignore
    AVAILABLE_COMPRESSION_LEVELS.append(11)
except ImportError:
    zopfli_gzip = None

# Zopfli performs in memory compression
ZOPFLI_MAXIMUM_SIZE = 50 * 1024 * 1024

# If isal is present we can perform much faster decompression.
try:
    from isal import isal_zlib
    zlib_decompressobj = isal_zlib.decompressobj
except ImportError:
    zlib_decompressobj = zlib.decompressobj  # type: ignore

# If xxhash is present we can perform much faster checksumming
try:
    import xxhash  # type: ignore
    DEFAULT_HASH_ALGORITHM = xxhash.xxh3_128
except ImportError:
    pass
except AttributeError:
    warnings.warn(f"This xxhash version ({xxhash.VERSION}) does not have "
                  f"xxh3_128. Please update to version 2.0.0 or higher to "
                  f"make use of this hash.")


def hash_file_contents(filepath: Filepath,
                       hash_algorithm=DEFAULT_HASH_ALGORITHM,
                       block_size: int = DEFAULT_BLOCK_SIZE):
    is_gzip = os.fspath(filepath).endswith(".gz")
    # Using a zlib decompressor has much less overhead than using GzipFile.
    # This comes with a memory overhead of compression_ratio * block_size.
    decompressor = zlib_decompressobj(wbits=31)
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


def compress_path(filepath: Filepath,
                  compresslevel: int = DEFAULT_COMPRESSION_LEVEL,
                  block_size: int = DEFAULT_BLOCK_SIZE):
    output_filepath = os.fspath(filepath) + ".gz"
    if compresslevel == 11:
        if zopfli_gzip is None:
            raise ModuleNotFoundError(
                "Zopfli is not installed. Compressing with zopfli is not "
                "supported. "
                "Install zopfi with 'pip install zopfli'.")
        if os.stat(filepath).st_size > ZOPFLI_MAXIMUM_SIZE:
            warnings.warn(f"{filepath} is larger than {ZOPFLI_MAXIMUM_SIZE} "
                          f"bytes. Fallback to gzip compression level 9.")
            compresslevel = 9
        else:
            data = Path(filepath).read_bytes()
            compressed = zopfli_gzip.compress(data)
            Path(output_filepath).write_bytes(compressed)
            return
    with open(filepath, mode="rb") as input_h:
        with gzip.open(output_filepath, mode="wb", compresslevel=compresslevel
                       ) as output_h:
            while True:
                block = input_h.read(block_size)
                if block == b"":
                    return
                output_h.write(block)  # type: ignore


def compress_file_if_changed(filepath: Filepath,
                             compresslevel=DEFAULT_COMPRESSION_LEVEL,
                             hash_algorithm=DEFAULT_HASH_ALGORITHM,
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
    logging.debug(f"Compressing {filepath} with compression level "
                  f"{compresslevel}")
    compress_path(filepath, compresslevel)
    return result


def get_extension(filename: str):
    """
    The filename's extension, if any.

    This includes the leading period. For example: '.txt'
    """
    # Implementation copied from pathlib.PurePath.suffix()
    index = filename.rfind(".")
    if 0 < index < len(filename) - 1:
        return filename[index:]
    else:
        return ""


def find_static_files(dir: Filepath,
                      extensions: Set[str],
                      ) -> Generator[str, None, None]:
    for dir_entry in os.scandir(dir):  # type: os.DirEntry
        if dir_entry.is_file():
            # Cheap check to skip all the .gz files quickly. This is 4x faster
            # than getting the extension and checking it. Since half of the
            # files in the directory will be .gz files after a rerun this is
            # worth it.
            if dir_entry.name.endswith(".gz"):
                continue
            if get_extension(dir_entry.name) in extensions:
                yield dir_entry.path
        elif dir_entry.is_dir():
            yield from find_static_files(dir_entry.path, extensions)
        else:
            logging.debug(f"Skip {dir_entry.path}: unsupported extension")
        # TODO: Check if special behaviour is needed for symbolic links


def read_extensions_file(filepath: Filepath) -> Set[str]:
    with open(filepath, "rt") as input_h:
        return {line.strip() for line in input_h}


def gzip_static(dir: Filepath,
                extensions_file: Filepath = DEFAULT_EXTENSIONS_FILE,
                compresslevel: int = DEFAULT_COMPRESSION_LEVEL,
                hash_algorithm=DEFAULT_HASH_ALGORITHM,
                force: bool = False) -> Tuple[int, int, int]:
    results = [0, 0, 0]
    extensions = read_extensions_file(extensions_file)
    for static_file in find_static_files(dir, extensions):
        result = compress_file_if_changed(static_file, compresslevel,
                                          hash_algorithm, force)
        results[result] += 1
    return tuple(results)  # type: ignore  # 3 values are guaranteed


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=str,
                        help="The directory containing the static site")
    complevel = parser.add_mutually_exclusive_group()
    complevel.add_argument("-l", "--compression-level",
                           choices=AVAILABLE_COMPRESSION_LEVELS,
                           type=int,
                           default=DEFAULT_COMPRESSION_LEVEL,
                           help=f"The compression level that will be used for "
                                f"the gzip compression. Use 11 for zopfli "
                                f"compression (if available). "
                                f"Default: {DEFAULT_COMPRESSION_LEVEL}")
    complevel.add_argument("--zopfli", action="store_const", const=11,
                           dest="compression_level",
                           help="Use zopfli for the compression. Alias for "
                                "-l 11 or --compression-level 11.")
    parser.add_argument("-e", "--extensions-file", type=str,
                        default=DEFAULT_EXTENSIONS_FILE,
                        help="A file with extensions to consider when "
                             "compressing. Use one line per extension. "
                             "Check the default for an example.")
    parser.add_argument("-f", "--force", action="store_true",
                        help="Force recompression of all earlier compressed "
                             "files.")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Print debug information to stderr.")

    return parser


def main():
    args = argument_parser().parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    results = gzip_static(args.directory,
                          extensions_file=args.extensions_file,
                          compresslevel=args.compression_level,
                          force=args.force)
    print(f"New gzip files:     {results[COMPRESSED]}")
    print(f"Updated gzip files: {results[RECOMPRESSED]}")
    print(f"Skipped gzip files: {results[SKIPPED]}")
