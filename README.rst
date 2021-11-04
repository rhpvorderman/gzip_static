.. image:: https://img.shields.io/pypi/v/gzip_static.svg
  :target: https://pypi.org/project/gzip_static/
  :alt:

.. image:: https://img.shields.io/pypi/pyversions/gzip_static.svg
  :target: https://pypi.org/project/gzip_static/
  :alt:

.. image:: https://img.shields.io/pypi/l/gzip_static.svg
  :target: https://github.com/LUMC/isal/blob/main/LICENSE
  :alt:

.. image:: https://codecov.io/gh/rhpvorderman/gzip_static/branch/main/graph/badge.svg?token=NFFZIBF1ZA
  :target: https://codecov.io/gh/rhpvorderman/gzip_static

.. image:: https://readthedocs.org/projects/gzip_static/badge
   :target: https://gzip_static.readthedocs.io
   :alt:


gzip_static
===========

Compress your static website or website's static assets with gzip for faster
serving with nginx's gzip_static on.

nginx does not perform checks on the served gzip to determine if it is out of
date. This program was created to automate the checks and compression of the
static files at the website's build time.

Features:

+ Finds all static files in a directory and its subdirectory automatically
  based on an `extensions file <src/gzip_static/extensions.txt>`_ which can be
  customized.
+ `Idempotent <https://en.wikipedia.org/wiki/Idempotence>`_. Only compresses
  files that have not been compressed yet or are changed. Can therefore be used with
  configuration management systems such as `Ansible <https://www.ansible.com/>`_.
+ Guards against serving outdated gzips
    + Content is checked with a checksum to verify that a file has changed.
    + Has a ``--remove-orphans`` option to remove gzips for which the source
      static file is no longer available.
+ The created gzip files inherited filesystem attributes from the source static
  files such as the mode and the last modified time.
+ Works on any machine with Python 3.6 or higher installed. It does not depend
  on other packages for its core functionally.
+ Zopfli compression is supported when `zopfli <https://pypi.org/project/zopfli>`_
  is installed.
+ Can be used as a library in other projects and has a `fully documented API
  <https://gzip-static.readthedocs.io/en/latest/#module-gzip_static>`_.

Quickstart
==========

Install gzip_static with ``pip install gzip_static`` or ``pip install --user
gzip_static``. For more installation options and options to enable more
functionally such as zopfli and better speed, checkout `the installation
documentation <https://gzip-static.readthedocs.io/en/latest/#installation>`_.

+ To compress all static files in a directory:
  ``gzip-static /var/www/my_example_website/``
+ To check if all gzip files are up to date and recompress changed ones:
  ``gzip-static /var/www/my_example_website/`` (Same command due to idempotency)
+ To check if all gzip files are up to date, recompress changed ones and remove
  gzip files for which a source static file is no longer present:
  ``gzip-static --remove-orphans /var/www/my_example_website/``
+ To check for orphaned files only: ``gzip-static-find-orphans /var/www/my_example_website/``

For a more extended usage and more options use ``gzip-static --help`` or
checkout `the usage documentation
<https://gzip-static.readthedocs.io/en/latest/#usage>`_.