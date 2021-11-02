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

No brotli support
-----------------
`Brotli <https://en.wikipedia.org/wiki/Brotli>`_ is an excellent compression
algorithm. Most browsers support it. There are several reasons why it is not
supported by gzip_static.

- The ngx_brotli module is not provided as a package by either Debian, Ubuntu
  or CentOS.
- Supporting two formats simultaneously makes the code more complex.
- `brotli_static does not work well with gzip_static <https://github.com/google/ngx_brotli/issues/123>`_

This project was made to work with NGiNX's gzip plugin to host my
websites. The gzip plugin is builtin in
even the simplest NGiNX package on Debian (``nginx-light``). Getting brotli to
work however is much more work. It needs to be compiled, but it needs to
compiled exactly with the right instructions. Brotli has been around
since 2013 and has tremendous advantages, but
ngx_brotli has not been packaged in Debian for 8 years. The last release
of Debian (bullseye) `had 11294 new packages
<https://www.debian.org/News/2021/20210814>`_ but ngx_brotli is nowhere on the
horizon.

Once a properly working ngx_brotli module is packaged in Debian, I am happy
to add brotli support!
