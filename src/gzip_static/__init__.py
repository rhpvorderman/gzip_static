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


"""Functions to compress a website's static files."""
import argparse
import gzip
import hashlib
import io
import logging
import os
import typing
import warnings
import zlib
from pathlib import Path
from typing import Container, Generator, Set, Union

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
DELETED = 3

DEFAULT_EXTENSIONS_FILE = Path(__file__).parent / "extensions.txt"
DEFAULT_EXTENSIONS = frozenset(
    DEFAULT_EXTENSIONS_FILE.read_text("UTF-8").strip().split("\n"))

# Limit CLI compresslevels to 6, 9 and 11 to keep CLI clean.
AVAILABLE_COMPRESSION_LEVELS = [6, 9, 11]

try:
    from zopfli import gzip as zopfli_gzip  # type: ignore
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


class GzipStaticResult(typing.NamedTuple):
    """
    A class containing the results for the gzip_static function.
    """
    created: int
    updated: int
    skipped: int
    deleted: int


def hash_file_contents(filepath: Filepath,
                       hash_algorithm=DEFAULT_HASH_ALGORITHM,
                       block_size: int = DEFAULT_BLOCK_SIZE) -> bytes:
    """
    Read contents from a file and return the hash.

    :param filepath: The path to the file. Paths ending in '.gz' will be
                     automatically decompressed.
    :param hash_algorithm: The hash algorithm to use. Must be
                           hashlib-compatible.
    :param block_size: The size of the chunks read from the file at once.
    :return: A digest of the hash.
    """
    is_gzip = os.fspath(filepath).endswith(".gz")
    if is_gzip:
        # Using a zlib decompressor has much less overhead than using GzipFile.
        # This comes with a memory overhead of compression_ratio * block_size.
        decompressor = zlib_decompressobj(wbits=31)
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
                  block_size: int = DEFAULT_BLOCK_SIZE) -> None:
    """
    Compress a file's contents and write them to a '.gz' file.

    Similar to gzip -k <filepath>

    :param filepath: The path to the file
    :param compresslevel: The gzip compression level to use. Use 11 for zopfli
                          compression.
    :param block_size: The size of the chunks read from the file at once.
    """
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


def compress_idempotent(filepath: Filepath,
                        compresslevel=DEFAULT_COMPRESSION_LEVEL,
                        hash_algorithm=DEFAULT_HASH_ALGORITHM,
                        force: bool = False) -> int:
    """
    Only compress the file if no companion .gz is present that contains the
    correct contents.

    This function ensures the mode, atime and mtime of the gzip file are
    inherited from the file to be compressed.

    :param filepath: The path to the file.
    :param compresslevel: The compression level. Use 11 for zopfli.
    :param hash_algorithm: The hash_algorithm to check the contents with.
    :param force: Always create a new '.gz' file to overwrite the old one.
    :return: An integer that stands for the action taken. Matches with
             the COMPRESSED, RECOMPRESSED and SKIPPED constants in this module.
    """
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

    # Set filesystem attributes for the gzipped file.
    file_stat = os.stat(filepath)
    os.utime(gzipped_path, ns=(file_stat.st_atime_ns, file_stat.st_mtime_ns))
    os.chmod(gzipped_path, file_stat.st_mode)
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
                      extensions: Container[str] = DEFAULT_EXTENSIONS,
                      ) -> Generator[str, None, None]:
    """
    Scan a directory recursively for files that have an extension in the set
    of extensions.

    :param dir: The directory to scan.
    :param extensions: A set of extensions to scan for.
    :return: A generator of filepaths that match the extensions.
    """
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
            else:
                logging.debug(f"Skip {dir_entry.path}: unsupported extension")
        elif dir_entry.is_dir():
            yield from find_static_files(dir_entry.path, extensions)
        # TODO: Check if special behaviour is needed for symbolic links


def find_orphaned_files(dir: Filepath,
                        extensions: Container[str] = DEFAULT_EXTENSIONS
                        ) -> Generator[str, None, None]:
    """
    Scan a directory recursively for '.gz' files that do not have a parent file
    with an extension in extensions.

    For example ``find_orphaned_files(my_dir, set(".html"))`` will find
    ``index.html.gz`` if ``index.html`` is not present. It will not find
    ``myhostedarchive.tar.gz`` as ``.tar`` is not in the set of extensions.

    :param dir: The directory to scan.
    :param extensions: Extensions of parents file to include.
    :return: A generator of filepaths of orphaned '.gz' files.
    """
    for dir_entry in os.scandir(dir):  # type: os.DirEntry
        if dir_entry.is_file():
            if dir_entry.name.endswith(".gz"):
                parent_file = dir_entry.path[:-3]
                if get_extension(parent_file) in extensions:
                    if not os.path.exists(parent_file):
                        yield dir_entry.path
        elif dir_entry.is_dir():
            yield from find_orphaned_files(dir_entry.path, extensions)


def read_extensions_file(filepath: Filepath) -> Set[str]:
    """
    Read a file where there is an extension on each line

    :param filepath: The extensions file
    :return: a set of extensions.
    """
    with open(filepath, "rt") as input_h:
        return {line.strip() for line in input_h}


def gzip_static(dir: Filepath,
                extensions: Container[str] = DEFAULT_EXTENSIONS,
                compresslevel: int = DEFAULT_COMPRESSION_LEVEL,
                hash_algorithm=DEFAULT_HASH_ALGORITHM,
                force: bool = False,
                remove_orphans: bool = False) -> GzipStaticResult:
    """
    Gzip all static files in a directory and its subdirectories in an
    idempotent manner.

    :param dir: The directory to recurse through.
    :param extensions: Extensions which are static files.
    :param compresslevel: The compression level that is used when compressing.
    :param hash_algorithm: The hash algorithm is used when checking file
                           contents.
    :param force: Recompress all files regardless if content has changed or
                  not.
    :param remove_orphans: Remove '.gz' files where the parent static file is
                           no longer present.
    :return: A tuple with 4 entries. The number of compressed, recompressed,
             skipped and deleted gzip files.
    """
    results = [0, 0, 0, 0]
    for static_file in find_static_files(dir, extensions):
        result = compress_idempotent(static_file, compresslevel,
                                     hash_algorithm, force)
        results[result] += 1
    if remove_orphans:
        for orphaned_file in find_orphaned_files(dir, extensions):
            logging.warning(
                f"Found orphaned file: {orphaned_file}. Deleting...")
            os.remove(orphaned_file)
            results[DELETED] += 1
    return GzipStaticResult(*results)


def common_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=str,
                        help="The directory containing the static site")
    parser.add_argument("-e", "--extensions-file", type=str,
                        default=DEFAULT_EXTENSIONS_FILE,
                        help=f"A file with extensions to consider when "
                             f"compressing. Use one line per extension. "
                             f"Check the default for an example. DEFAULT: "
                             f"{DEFAULT_EXTENSIONS_FILE}")
    return parser


def argument_parser() -> argparse.ArgumentParser:
    parser = common_parser()
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
    parser.add_argument("-f", "--force", action="store_true",
                        help="Force recompression of all earlier compressed "
                             "files.")
    parser.add_argument("--remove-orphans", action="store_true",
                        help="Remove gzip files for which the parent file is "
                             "missing and for which the extension is in the "
                             "extensions file. For example: page3.html.gz "
                             "present but no page3.html is present. "
                             "In that case page3.html.gz will be removed.")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Print debug information to stderr.")

    return parser


def find_orphans_main():
    args = common_parser().parse_args()
    for file in find_orphaned_files(
            args.directory, read_extensions_file(args.extensions_file)):
        print(file)


def main():
    args = argument_parser().parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    extensions = read_extensions_file(args.extensions_file)
    results = gzip_static(args.directory,
                          extensions=extensions,
                          compresslevel=args.compression_level,
                          force=args.force,
                          remove_orphans=args.remove_orphans)
    changes = bool(results.created + results.updated + results.deleted)
    if changes:
        print(f"{args.directory} was updated")
    else:
        print(f"{args.directory} had no changes")
    print(f"Created gzip files: {results.created}")
    print(f"Updated gzip files: {results.updated}")
    print(f"Skipped gzip files: {results.skipped}")
    print(f"Deleted gzip files: {results.deleted}")
