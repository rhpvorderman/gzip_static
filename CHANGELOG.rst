==========
Changelog
==========

.. Newest changes should be on top.

.. This document is user facing. Please word the changes in such a way
.. that users understand how the changes affect the new version.

version 0.1.0-dev
------------------
+ Publish documentation on readthedocs.
+ Make sure the gzip files inherit file attributes from the parent file.
+ Add functionality to remove orphaned gzip files.
+ Speed up the checksumming process with isal and xxhash.
+ Add zopfli support.
+ Create functions to compress a website's static assets idempotently.
