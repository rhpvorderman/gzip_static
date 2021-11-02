=============
Installation
=============

gzip_static can be installed with ``pip install gzip_static``. There are no
dependencies by default.

The following packages can be installed to enhance the functionality of
gzip_static.

+ `zopfli <https://pypi.org/project/zopfli/>`_ adds zopfli compression to
  gzip_static. Zopfli compressed files can be decompressed with any
  gzip-compatible tool and the compressed size is a few percent smaller than
  files compressed with gzip level 9. This comes with much increased
  compression time (~125x increase or thereabouts depending on the website).
  This works great for files that aren't changed much or at all but always
  downloaded like stylesheets.
+ `xxhash <https://pypi.org/project/xxhash/>`_ speeds up the checksumming process.
  This makes gzip-static about 28% faster when running on a website folder
  with all the gzip files up to date.
+ `isal <https://pypi.org/project/isal/>`_ speeds up the decompression of gzip
  files during the checksumming process. This makes gzip-static about 66% faster
  when running on a website folder with all the gzip files up to date.
  Isal is only available on 64-bit platforms.

Together xxhash and isal decrease the runtime of checksumming by about 60%,
so it is about 2.5 times faster.

These dependencies are all optional and can be installed separately in the
environment or with the optional dependency commands:

+ `pip install gzip_static[zopfli]` installs gzip_static and zopfli.
+ `pip install gzip_static[performance]` installs gzip_static, xxhash and isal.
+ `pip install gzip_static[full]` installs gzip_static, zopfli, xxhash and isal.
