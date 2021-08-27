#!/usr/bin/env python3
"""
Purpose : Tests canopycover.py
Author : Ken Youens-Clark <kyclark@arizona.edu>
         Chris Schnaufer <schnaufer@arizona.edu>
"""
import csv
import json
import os
import random
import re
import string
from shutil import rmtree
from subprocess import getstatusoutput

# The name of the source file to test and it's path
SOURCE_FILE = 'canopycover.py'
SOURCE_PATH = os.path.abspath(os.path.join('.', SOURCE_FILE))

# Path relative to the current folder where the testing JSON file are
TESTING_JSON_FILE_PATH = os.path.realpath('./test_data')

# Path to files to use for testing
META = os.path.abspath(os.path.join(TESTING_JSON_FILE_PATH, 'meta.yaml'))
INPUT1 = os.path.abspath(os.path.join(TESTING_JSON_FILE_PATH, 'rgb_17_7_W.tif'))
INPUT_NO_ALPHA = os.path.abspath(os.path.join(TESTING_JSON_FILE_PATH, 'three_channel_mask.tif'))


def random_string():
    """generate a random string"""
    k = random.randint(5, 10)
    return ''.join(random.choices(string.ascii_letters + string.digits, k=k))


def test_exists():
    """Asserts that the source file is available"""
    assert os.path.isfile(SOURCE_PATH)


def test_usage():
    """Program prints a "usage" statement when requested"""
    for flag in ['-h', '--help']:
        ret_val, out = getstatusoutput(f'{SOURCE_PATH} {flag}')
        assert re.match('usage', out, re.IGNORECASE)
        assert ret_val == 0


def test_no_args():
    """
    Verify that the program dies on no arguments
    Currently the program has a return value of 0
    when provided no arguments. I recommend this be
    changed to some non-zero value to indicate a failure.
    """
    ret_val, out = getstatusoutput(SOURCE_PATH)
    assert ret_val != 0
    assert re.search('Unable to find an image file to work with', out)


def test_no_image_files():
    """
    Verify that the program returns an error when
    no file_list is given
    """
    cmd = f'{SOURCE_PATH} --metadata {META}'
    ret_val, out = getstatusoutput(cmd)
    assert ret_val != 0
    assert re.search('Unable to find an image file to work with', out)


def test_no_metadata():
    """ Run with a file but no metadata"""
    out_dir = random_string()

    # This ought not be necessary as the program *should*
    # create it; for now, we'll create the output dir.
    os.makedirs(out_dir)

    try:
        cmd = f'{SOURCE_PATH} --working_space {out_dir} {INPUT1}'
        ret_val, _ = getstatusoutput(cmd)
        assert ret_val == 0

        results = os.path.join(out_dir, 'result.json')
        assert os.path.isfile(results)

        with open(results, encoding='utf-8') as res_file:
            result = json.load(res_file)
        assert 'files' in result
        out_files = [f['path'] for f in result['files']]

        canopycover = f'{out_dir}/canopycover.csv'
        assert canopycover in out_files

        assert os.path.isfile(canopycover)

        with open(canopycover, encoding='utf-8') as cc_file:
            canopy = csv.DictReader(cc_file)
            canopy_flds = [
                'local_datetime', 'canopy_cover', 'species', 'site', 'method'
            ]
            assert canopy.fieldnames == canopy_flds

            canopy_data = list(canopy)
            assert len(canopy_data) == 1

            assert canopy_data[0]['canopy_cover'] == '99.8'

    finally:
        if os.path.isdir(out_dir):
            rmtree(out_dir)


def test_no_metadata_no_alpha():
    """ Run with a file that doesn't have an alpha channel, and with no metadata"""
    out_dir = random_string()

    # This ought not be necessary as the program *should*
    # create it; for now, we'll create the output dir.
    os.makedirs(out_dir)

    try:
        cmd = f'{SOURCE_PATH} --working_space {out_dir} {INPUT_NO_ALPHA}'
        ret_val, _ = getstatusoutput(cmd)
        assert ret_val == 0

        results = os.path.join(out_dir, 'result.json')
        assert os.path.isfile(results)

        with open(results, encoding='utf-8') as res_file:
            result = json.load(res_file)
        assert 'files' in result
        out_files = [f['path'] for f in result['files']]

        canopycover = f'{out_dir}/canopycover.csv'
        assert canopycover in out_files

        assert os.path.isfile(canopycover)

        with open(canopycover, encoding='utf-8') as cc_file:
            canopy = csv.DictReader(cc_file)
            canopy_flds = [
                'local_datetime', 'canopy_cover', 'species', 'site', 'method'
            ]
            assert canopy.fieldnames == canopy_flds

            canopy_data = list(canopy)
            assert len(canopy_data) == 1

            assert canopy_data[0]['canopy_cover'] == '1.05'

    finally:
        if os.path.isdir(out_dir):
            rmtree(out_dir)


def test_get_fields():
    """Fetches the fields"""
    # pylint: disable=import-outside-toplevel
    import canopycover as cc

    field_list = cc.get_fields()
    assert len(field_list) > 0
    assert isinstance(field_list, list)


def test_fail_get_default_trait():
    """Checks getting a default value for a unknown field"""
    # pylint: disable=import-outside-toplevel
    import canopycover as cc

    def_trait = cc.get_default_trait('not a valid field')
    assert isinstance(def_trait, str)
    assert len(def_trait) == 0


def test_get_default_trait():
    """Checks getting a default value for known fields"""
    # pylint: disable=import-outside-toplevel
    import canopycover as cc

    # Check that we get an empty list back
    for one_field in cc.TRAIT_NAME_ARRAY_VALUE:
        def_trait = cc.get_default_trait(one_field)
        assert isinstance(def_trait, list)
        assert len(def_trait) == 0

    for one_field in cc.TRAIT_NAME_MAP:
        def_trait = cc.get_default_trait(one_field)
        assert isinstance(def_trait, str)
        assert len(def_trait) > 0


def test_get_traits_table():
    """Check getting the traits table information"""
    # pylint: disable=import-outside-toplevel
    import canopycover as cc

    trait_table = cc.get_traits_table()
    assert isinstance(trait_table, list)
    assert len(trait_table) == 2
    assert isinstance(trait_table[0], list)
    assert isinstance(trait_table[1], dict)
    assert len(trait_table[0]) > 0
    assert len(trait_table[1].keys()) > 0
    assert len(trait_table[0]) == len(trait_table[1].keys())


def test_generate_traits_list():
    """Check getting traits list"""
    # pylint: disable=import-outside-toplevel
    import canopycover as cc

    data_file_name = os.path.join(TESTING_JSON_FILE_PATH, 'generate_traits_list.json')
    assert os.path.exists(data_file_name)

    # Check fields for each entry from test file
    fields = cc.get_fields()
    with open(data_file_name, 'r', encoding='utf-8') as in_file:
        test_data = json.load(in_file)
        for test in test_data:
            trait_list = cc.generate_traits_list(test)
            # Disable following check since we need the index value
            # pylint: disable=consider-using-enumerate
            for idx in range(0, len(fields)):
                if fields[idx] in test:
                    assert trait_list[idx] == test[fields[idx]]
                else:
                    assert trait_list[idx] == cc.get_default_trait(fields[idx])


def test_good_input():
    """Test with good inputs"""
    out_dir = random_string()

    # This ought not be necessary as the program *should*
    # create it; for now, we'll create the output dir.
    os.makedirs(out_dir)

    try:
        cmd = f'{SOURCE_PATH} --working_space {out_dir} --metadata {META} {INPUT1}'
        ret_val, _ = getstatusoutput(cmd)
        assert ret_val == 0

        results = os.path.join(out_dir, 'result.json')
        assert os.path.isfile(results)

        with open(results, encoding='utf-8') as res_file:
            result = json.load(res_file)
        assert 'files' in result
        out_files = [f['path'] for f in result['files']]

        canopycover = f'{out_dir}/canopycover.csv'
        assert canopycover in out_files

        assert os.path.isfile(canopycover)

        with open(canopycover, encoding='utf-8') as cc_file:
            canopy = csv.DictReader(cc_file)
            canopy_flds = [
                'local_datetime', 'canopy_cover', 'species', 'site', 'method'
            ]
            assert canopy.fieldnames == canopy_flds

            canopy_data = list(canopy)
            assert len(canopy_data) == 1

            assert canopy_data[0]['canopy_cover'] == '99.8'

    finally:
        if os.path.isdir(out_dir):
            rmtree(out_dir)
