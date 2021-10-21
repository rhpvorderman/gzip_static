gzip_static
===========

Compress your static website with gzip for faster serving with NGiNX's 
gzip_static on.

gzip_static compresses all static files with gzip and assures the content has
been changed before compressing again. It does so by performing a checksum on
the contents of the static file and its gzipped version. Guaranteeing that you
do not publish outdated gzip files.

Rationale
=========

`NGiNX <https://nginx.org/en/>`_ features a `gzip_static
<https://nginx.org/en/docs/http/ngx_http_gzip_static_module.html>`_ module that
enables the serving of pre-compressed gzip files. This makes the static
elements of your website load much faster if there is a precompressed file with
the ``.gz`` extension present.

There is a slight problem though: NGiNX does not check whether the gzipped
version of the file is up to date with the actual file. To solve this it is
best to manage precompression with a program that performs this check.

Most programs out there are linked to a specific framework and most stand-alone
programs are written in bash and do not perform checks. One notable exception
is `static-compress <https://github.com/neosmart/static-compress>`_
which performs timestamp checking.

Timestamp checking is not good enough in my opinion. The actual content of the
gzipped file should be checked. Hence this program.