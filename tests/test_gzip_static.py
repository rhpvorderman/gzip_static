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

import gzip
import hashlib
import os
import shutil
import tempfile
from pathlib import Path

from gzip_static import COMPRESSED, RECOMPRESSED, SKIPPED, \
    hash_file_contents, compress_path, \
    compress_file_if_changed, get_extension, find_static_files, \
    read_extensions_file, gzip_static, main

import pytest

import xxhash

DATA = b"This is a test string with some compressable data."

@pytest.mark.parametrize(["filename", "extension"], [
    ("NO_EXTENSION", ""),
    ("compressed.gz", ".gz"),
    ("a.lot.of.extionsions.ext", ".ext")
])
def test_get_extension(filename, extension):
    assert get_extension(filename) == extension


@pytest.mark.parametrize("hash_func", [xxhash.xxh3_128, hashlib.sha1])
def test_hash_file_contents(hash_func):
    test_dir = Path(tempfile.mkdtemp())
    test_file = Path(test_dir, "test_file")
    test_file.write_bytes(DATA)
    assert hash_file_contents(test_file, hash_func) == hash_func(DATA).digest()
    test_gz = Path(test_dir, "test.gz")
    test_gz.write_bytes(gzip.compress(DATA))
    assert hash_file_contents(test_gz, hash_func) == hash_func(DATA).digest()
    shutil.rmtree(test_dir)


@pytest.mark.parametrize("compresslevel", [6, 9, 11])
def test_compress_path(compresslevel):
    test_dir = Path(tempfile.mkdtemp())
    test_file = test_dir / "test_file"
    test_file.write_bytes(DATA)
    compress_path(test_file, compresslevel=compresslevel)
    gzipped_file = Path(os.fspath(test_file) + ".gz")
    assert gzipped_file.exists()
    assert gzip.decompress(gzipped_file.read_bytes()) == DATA
    shutil.rmtree(test_dir)


def test_read_extensions_file():
    fd, name = tempfile.mkstemp()
    os.close(fd)
    test = Path(name)
    test.write_text(".html\n.js")
    assert read_extensions_file(test) == {".html", ".js"}
    test.unlink()


def test_compress_file_if_changed_no_change():
    test_dir = Path(tempfile.mkdtemp())
    test_file = test_dir / "test"
    test_gz = test_dir / "test.gz"
    test_file.write_bytes(DATA)
    test_gz.write_bytes(gzip.compress(DATA))
    assert compress_file_if_changed(test_file) == SKIPPED


def test_compress_file_if_changed_force():
    test_dir = Path(tempfile.mkdtemp())
    test_file = test_dir / "test"
    test_gz = test_dir / "test.gz"
    test_file.write_bytes(DATA)
    test_gz.write_bytes(gzip.compress(DATA))
    assert compress_file_if_changed(test_file, force=True) == RECOMPRESSED


def test_compress_file_if_changed_changed():
    test_dir = Path(tempfile.mkdtemp())
    test_file = test_dir / "test"
    test_gz = test_dir / "test.gz"
    test_file.write_bytes(DATA + b" Some changes were made.")
    test_gz.write_bytes(gzip.compress(DATA))
    assert compress_file_if_changed(test_file) == RECOMPRESSED


def test_compress_file_if_changed_no_companion_gz():
    test_dir = Path(tempfile.mkdtemp())
    test_file = test_dir / "test"
    test_gz = test_dir / "test.gz"
    test_file.write_bytes(DATA)
    assert not test_gz.exists()
    assert compress_file_if_changed(test_file) == COMPRESSED
    assert test_gz.exists()
