Checksum choice
###############

Different checksums were considered. MD5 is traditionally used for
checksumming, but also SHA-1, SHA-256 and SHA-512 see use as a hashing
algorithm nowadays.

Traditionally, cyclic redundancy checks are performed. These are available in
the Python ``zlib`` libraries as the ``crc32`` and ``adler32`` functions.

A fast method called `XXHash <https://cyan4973.github.io/xxHash/>`_ is also
available nowadays for hashing. There are Python bindings available as a
package on PyPI.

The hashing algorithms `were benchmarked <benchmarks/hashing_algorithms.txt>`_
and several conclusions can be drawn.

- MD5 is one of the slowest algorithms
- sha1sum is the fastest algorithm in Python's hashlib
- XXHash is about 10 times faster than sha1sum.
- The cyclic redundancy checks fair poorly. Zlib.crc32 is slower than sha1sum.
  adler32 is only 40% faster than sha1sum.

https://bleepcoder.com/xxhash/468794876/xxhash-as-checksum-for-error-detection