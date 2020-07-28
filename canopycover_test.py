#!/usr/bin/env python3
"""
Purpose: Tests for canopycover.py
Author : Ken Youens-Clark <kyclark@arizona.edu>
"""

import os
import re
import random
import string
import json
from subprocess import getstatusoutput
from shutil import rmtree

prg = './canopycover.py'
meta = './test_data/meta.yaml'
input1 = './test_data/rgb_17_7_W.tif'


# --------------------------------------------------
def test_exists():
    """
    Program exists
    """

    assert os.path.isfile(prg)


# --------------------------------------------------
def test_usage():
    """
    Program prints a "usage" statement when requested
    """

    for flag in ['-h', '--help']:
        rv, out = getstatusoutput(f'{prg} {flag}')
        assert rv == 0
        assert re.match("usage", out, re.IGNORECASE)


# --------------------------------------------------
def test_no_args():
    """
    Verify that the program dies on no arguments
    Currently the program has a return value of 0
    when provided no arguments. I recommend this be
    changed to some non-zero value to indicate a failure.
    """

    rv, out = getstatusoutput(prg)
    assert rv == 0  # This seems like a problem!
    assert re.match('No metadata paths were specified', out)


# --------------------------------------------------
def test_file_input():
    """
    Run with a file
    """

    rv, out = getstatusoutput(f'{prg} {input1}')
    assert rv == 0  # This seems like a problem!
    assert re.match("a file path wasn't provided", out)


# --------------------------------------------------
def test_good_input():
    """
    Test with good inputs
    """

    out_dir = random_string()

    # This ought not be necessary as the program *should*
    # create it; for now, we'll create the output dir.
    os.makedirs(out_dir)

    try:
        rv, out = getstatusoutput(f'{prg} --metadata {meta} {input1}')
        assert rv == 0
        result = json.loads(out)
        assert 'files' in result

        out_files = [f['path'] for f in result['files']]
        geostreams = 'output/canopycover_geostreams.csv'
        canopycover = 'output/canopycover.csv'
        assert geostreams in out_files
        assert canopycover in out_files
        assert os.path.isfile(geostreams)
        assert os.path.isfile(canopycover)
    finally:
        if os.path.isdir(out_dir):
            rmtree(out_dir)


# --------------------------------------------------
def random_string():
    """generate a random string"""

    k = random.randint(5, 10)
    return ''.join(random.choices(string.ascii_letters + string.digits, k=k))
