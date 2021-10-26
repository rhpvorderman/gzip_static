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
import os
import shutil
import sys
import tempfile
from pathlib import Path

from gzip_static import COMPRESSED, DEFAULT_EXTENSIONS_FILE, \
    DEFAULT_HASH_ALGORITHM, RECOMPRESSED, SKIPPED, compress_file_if_changed, \
    compress_path, find_static_files, get_extension, gzip_static, \
    hash_file_contents, main, read_extensions_file

import pytest

try:
    import zopfli
except ImportError:
    zopfli = None

DATA = b"This is a test string with some compressable data."


@pytest.mark.parametrize(["filename", "extension"], [
    ("NO_EXTENSION", ""),
    ("compressed.gz", ".gz"),
    ("a.lot.of.extionsions.ext", ".ext")
])
def test_get_extension(filename, extension):
    assert get_extension(filename) == extension


def test_hash_file_contents():
    hash_func = DEFAULT_HASH_ALGORITHM
    test_dir = Path(tempfile.mkdtemp())
    test_file = Path(test_dir, "test_file")
    test_file.write_bytes(DATA)
    assert hash_file_contents(test_file, hash_func) == hash_func(DATA).digest()
    test_gz = Path(test_dir, "test.gz")
    test_gz.write_bytes(gzip.compress(DATA))
    assert hash_file_contents(test_gz, hash_func) == hash_func(DATA).digest()
    shutil.rmtree(test_dir)


@pytest.mark.parametrize("compresslevel", [6, 9])
def test_compress_path(compresslevel):
    test_dir = Path(tempfile.mkdtemp())
    test_file = test_dir / "test_file"
    test_file.write_bytes(DATA)
    compress_path(test_file, compresslevel=compresslevel)
    gzipped_file = Path(os.fspath(test_file) + ".gz")
    assert gzipped_file.exists()
    assert gzip.decompress(gzipped_file.read_bytes()) == DATA
    shutil.rmtree(test_dir)


@pytest.mark.skipif(bool(zopfli),
                    reason="Test exception when zopfli is not installed")
def test_compress_path_no_zopfli():
    test_dir = Path(tempfile.mkdtemp())
    test_file = test_dir / "test_file"
    test_file.write_bytes(DATA)
    with pytest.raises(ModuleNotFoundError) as error:
        compress_path(test_file, compresslevel=11)
    error.match("zopfli")


@pytest.mark.skipif(not bool(zopfli),
                    reason="Test function normally when zopfli is installed")
def test_compress_path_zopfli():
    test_dir = Path(tempfile.mkdtemp())
    test_file = test_dir / "test_file"
    test_file.write_bytes(DATA)
    compress_path(test_file, compresslevel=11)
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


def test_find_static_files():
    test_dir = Path(tempfile.mkdtemp())
    (test_dir / "sub_dir").mkdir()
    (test_dir / "index.html").touch()
    (test_dir / "archive.tar.gz").touch()
    (test_dir / "sub_dir" / "some.js").touch()
    (test_dir / "sub_dir" / "some.css").touch()
    (test_dir / "notgzippable.png").touch()
    assert set(
        find_static_files(test_dir,
                          read_extensions_file(DEFAULT_EXTENSIONS_FILE))
    ) == {str(test_dir / "index.html"),
          str(test_dir / "sub_dir" / "some.js"),
          str(test_dir / "sub_dir" / "some.css")}
    shutil.rmtree(test_dir)


def test_gzip_static():
    test_dir = Path(tempfile.mkdtemp())
    Path(test_dir, "index.html").write_bytes(b"bla")
    Path(test_dir, "index.html.gz").write_bytes(gzip.compress(b"bla"))
    Path(test_dir, "bla.js").write_bytes(b"bla")
    Path(test_dir, "my.css").write_bytes(b"blabla")
    Path(test_dir, "my.css.gz").write_bytes(gzip.compress(b"bla"))
    results = gzip_static(test_dir)
    assert results[COMPRESSED] == 1
    assert results[RECOMPRESSED] == 1
    assert results[SKIPPED] == 1
    assert Path(test_dir, "bla.js.gz").exists()
    assert gzip.decompress(Path(test_dir, "my.css.gz").read_bytes()
                           ) == b"blabla"


def test_main(capsys):
    test_dir = Path(tempfile.mkdtemp())
    Path(test_dir, "index.html").write_bytes(b"bla")
    Path(test_dir, "index.html.gz").write_bytes(gzip.compress(b"bla"))
    Path(test_dir, "bla.js").write_bytes(b"bla")
    Path(test_dir, "my.css").write_bytes(b"blabla")
    Path(test_dir, "my.css.gz").write_bytes(gzip.compress(b"bla"))
    sys.argv =["", str(test_dir), "--debug"]
    main()
    result = capsys.readouterr()
    assert "New gzip files:     1" in result.out
    assert "Updated gzip files: 1" in result.out
    assert "Skipped gzip files: 1" in result.out
    assert Path(test_dir, "bla.js.gz").exists()
    assert gzip.decompress(Path(test_dir, "my.css.gz").read_bytes()
                           ) == b"blabla"
