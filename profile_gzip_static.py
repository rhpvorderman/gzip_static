import cProfile
import sys

import gzip_static


def run_gzip_static():
    gzip_static.gzip_static(sys.argv[1])


if __name__ == "__main__":
    cProfile.run("run_gzip_static()")
