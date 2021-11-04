========================
Technical considerations
========================

Choosing a checksum
--------------------

Different checksums were considered. MD5 is traditionally used for
checksumming, but also SHA-1, SHA-256 and SHA-512 see use as a hashing
algorithm nowadays. Traditionally, cyclic redundancy checks are performed.
These are available in the Python ``zlib`` libraries as the ``crc32`` and
``adler32`` functions. A fast method called `XXHash
<https://cyan4973.github.io/xxHash/>`_ is also available nowadays for hashing.
There are Python bindings available as a
package on PyPI.

As highlighted in `this answer on bleepcoder by the XXHash author
<https://bleepcoder.com/xxhash/468794876/xxhash-as-checksum-for-error-detection>`_
cyclic redundancy checks have slightly worse collisions than modern hash
algorithms.

The `XXHash homepage <https://cyan4973.github.io/xxHash/>`_ has a list of
algorithms and their speeds. The ``SHA1`` hash algorithm is the fastest
algorithm available in ``hashlib.algorithms_guaranteed``.
(This was verified on two different PC's). Therefore it was chosen as default.
The XXH3_128 algorithm is used when XXhash is installed.

Speedy hashing of small gzip files
----------------------------------
Speedy hashing of normal files is quite easy. Open a file, read it in blocks,
feed each block to the hasher and get a checksum in the end. Choose a decent
block size to speed it up slightly. (32K was used here. 128K is used by ``cat``
so choosing more than Python's default of 8K is quite common).

Speedy hashing of gzip files presents a problem. We can simply use Python's
``gzip.open`` which returns a ``GzipFile``, but that is slow. Just like normal
``open`` this creates an interface to read the file, but then it gets more
complicated. This gets wrapped into a ``_PaddedFile`` object which is then
wrapped into a ``_GzipReader`` object which is then wrapped by the ``GzipFile``.
All these layers solve two problems:

- A controlled number of bytes can be read from the compressed file. Since the
  compression ratio can differ along the file it is impossible to grab a
  certain number of bytes and exactly know the size of the output once
  decompressed. ``_GzipReader.read`` has mechanisms built-in to always output
  the desired numbers of bytes.
- Gzip allows for multiple members (each consisting of header, compressed body and
  trailer) to be concatenated together. After a member is decompressed the
  remaining bytes in the file must be checked for another gzip member.

This functionality creates a lot of overhead. Using Python's ``zlib.decompress``
with ``wbits=31`` solves this problem as it can compress an in-memory block
in its entirety. It cannot read multiple members but since these gzip files
are compressed by gzip_static itself we know they only contain one member.

However this presents another problem: files have to be read in memory entirely.
This was solved by using a ``zlib.decompressobj`` instead and using the
``decompress`` method on that object. This works with streaming decompression.
It is not a problem that we do not know before which number of bytes is returned
by the function. This is typically in the 3-6 times the input bytes range.
At best gzip can compress at ratios of ~1000x. (Tested with all zeroes binary,
all ones binary, and a repetition of a single character). So if the input
block size is 8k, we can expect at most 8M bytes be read in memory. This is
acceptable, and this way even large static files of several hundreds of MB can
be checksummed in a streaming fashion.

The great advantage of this method is that most gzip's will be smaller than 8k.
So only one decompress call is needed. This is almost as fast as in-memory
decompression with ``zlib.decompress`` but allowing streaming.

For example on docs.python.org compressing the static files compresses 6374
static files with a combined size of 481 MB. The resulting gzip sizes are
as follows.

- gzip 8K or below (one decompress call): 3516
- gzip 8K - 16K (two decompress calls): 1560
- gzip 16K -24K (three decompress calls): 565
- gzip 24K - 32K (four decompress calls): 308
- gzip 32k-64k (eight or less decompress calls): 356
- gzip larger than 64k: 69

In total 6305 (99%!) of the gzip files are smaller than 64K and can be
decompressed with eight or less calls. Since the ``gzip.GzipFile`` overhead
weighs in very heavy at these small file sizes using ``zlib.decompressobj``
creates a notable speed improvement, reducing decompression time by about
~30% for the docs.python.org website.

The speedup can be even greater when using
`python-isal <https://github.com/pycompression/python-isal>`_. Using its
``isal_zlib.decompressobj`` reduces the decompression time with more than 50%.

No brotli support
-----------------
`Brotli <https://en.wikipedia.org/wiki/Brotli>`_ is an excellent compression
algorithm. Most browsers support it. There are several reasons why it is not
supported by gzip_static.

- The ngx_brotli module is not provided as a package by either Debian, Ubuntu
  or CentOS.
- Supporting two formats simultaneously makes the code more complex.
- `brotli_static does not work well with gzip_static <https://github.com/google/ngx_brotli/issues/123>`_

This project was made to work with nginx's gzip plugin to host my
websites. The gzip plugin is builtin in
even the simplest nginx package on Debian (``nginx-light``). Getting brotli to
work however is much more work. It needs to be compiled, but it needs to
compiled exactly with the right instructions. Brotli has been around
since 2013 and has tremendous advantages, but
ngx_brotli has not been packaged in Debian for 8 years. The last release
of Debian (bullseye) `had 11294 new packages
<https://www.debian.org/News/2021/20210814>`_ but ngx_brotli is nowhere on the
horizon.

Once a properly working ngx_brotli module is packaged in Debian, I am happy
to add brotli support!
