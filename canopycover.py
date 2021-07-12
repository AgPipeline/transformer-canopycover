#!/usr/bin/env python3
"""Calculates canopy coverage for plots in georeferenced images
"""

import argparse
import copy
import datetime
import logging
import os
import subprocess
import tempfile
from typing import Union
import cv2
import numpy as np
from agpypeline import entrypoint, algorithm, geoimage
from agpypeline.checkmd import CheckMD
from agpypeline.environment import Environment
from osgeo import gdal, ogr

from configuration import ConfigurationCanopycover


# Array of trait names that should have array values associated with them
TRAIT_NAME_ARRAY_VALUE = ['canopy_cover', 'site']

# Mapping of default trait names to fixed values
TRAIT_NAME_MAP = {
    'species': 'Unknown',
    'method': 'Green Canopy Cover Estimation from Field Scanner RGB images'
}

# How many significant digits the calculated value has
SIGNIFICANT_DIGITS = 3


def _add_image_mask(source_file: str) -> np.ndarray:
    """Adds an  image mask to the specified file
    Arguments:
        source_file: the file to add a mask to
    Returns:
        Returns an array representing the image
    Exceptions:
        Throws a RuntimeError exception if a problem occurs
    """
    pixels = None
    caught_exception = False
    file_list_name, file_vrt_name, file_mask_name = (None, None, None)
    try:
        # Create the list file
        _, file_list_name = tempfile.mkstemp('.txt', 'list_')
        with open(file_list_name, 'w') as out_file:
            out_file.write(os.path.abspath(source_file))

        # Create the VRT (virtual) file name
        _, file_vrt_name = tempfile.mkstemp('.vrt')

        # Create the VRT file
        cmd = 'gdalbuildvrt -addalpha -srcnodata "-99 -99 -99" -overwrite -input_file_list ' + file_list_name +\
              ' ' + file_vrt_name
        subprocess.call(cmd, shell=True)

        # Generate the final tif image
        _, file_mask_name = tempfile.mkstemp('.tif')
        cmd = 'gdal_translate -co COMPRESS=LZW -co BIGTIFF=YES ' + file_vrt_name + ' ' + file_mask_name
        subprocess.call(cmd, shell=True)

        # Load the masked file
        raster = gdal.Open(file_mask_name)
        pixels = np.array(raster.ReadAsArray())

    except Exception:
        caught_exception = True
        if logging.getLogger().level == logging.DEBUG:
            logging.exception('Unable to generate alpha mask for image "%s"', source_file)
        else:
            logging.error('Exception caught trying to generate alpha mask for image "%s"', source_file)

    # Clean up
    if os.path.exists(file_list_name):
        os.remove(file_list_name)
    if os.path.exists(file_vrt_name):
        os.remove(file_vrt_name)
    if os.path.exists(file_mask_name):
        os.remove(file_mask_name)

    if caught_exception:
        raise RuntimeError('Exception detected while trying to generate alpha mask for image "%s"' % source_file)

    return pixels


def _add_image_mask_non_geo(pxarray: np.ndarray) -> np.ndarray:
    """Adds an alpha channel to an image that isn't geo-referenced
    Arguments:
        pxarray: the image array to add an alpha channel to
    Return:
        Returns the image with an alpha channel added
    Note: no check is made to see if the image already has an alpha channel
    """
    rolled_image = np.rollaxis(pxarray, 0, 3)
    channel1 = rolled_image[:, :, 0]
    channel2 = rolled_image[:, :, 1]
    channel3 = rolled_image[:, :, 2]
    alpha = np.ones(channel1.shape, dtype=channel1.dtype) * 255
    return np.rollaxis(cv2.merge((channel1, channel2, channel3, alpha)), 2, 0)


def get_fields() -> list:
    """Returns the supported field names as a list
    """
    return ['local_datetime', 'canopy_cover', 'species', 'site', 'method']


def get_default_trait(trait_name: str) -> Union[str, list]:
    """Returns the default value for the trait name
    Args:
       trait_name: the name of the trait to return the default value for
    Return:
        If the default value for a trait is configured, that value is returned. Otherwise
        an empty string is returned.
    """
    # pylint: disable=global-statement
    global TRAIT_NAME_ARRAY_VALUE
    global TRAIT_NAME_MAP

    if trait_name in TRAIT_NAME_ARRAY_VALUE:
        return []  # Return an empty list when the name matches
    if trait_name in TRAIT_NAME_MAP:
        return TRAIT_NAME_MAP[trait_name]

    return ""


def get_traits_table() -> list:
    """Returns the field names and default trait values

    Returns:
        A tuple containing the list of field names and a dictionary of default field values
    """
    # Compiled traits table
    fields = get_fields()
    traits = {}
    for field_name in fields:
        traits[field_name] = get_default_trait(field_name)

    return [fields, traits]


def generate_traits_list(traits: dict) -> list:
    """Returns an array of trait values

    Args:
        traits: contains the set of trait values to return

    Return:
        Returns an array of trait values taken from the traits parameter
    """
    # compose the summary traits
    fields = get_fields()
    trait_list = []
    for field_name in fields:
        if field_name in traits:
            trait_list.append(traits[field_name])
        else:
            trait_list.append(get_default_trait(field_name))

    return trait_list


def setup_default_traits(traits: dict, args: argparse.Namespace, full_md: list) -> dict:
    """Overrides trait values based upon command line parameters and loaded metadata
    Arguments:
        traits: the current set of traits
        args: command line arguments which may override values
        full_md: the loaded metadata which is checked for default values
    Return:
        A copy of the traits with updated values, or the original traits if nothing was changed
    """
    new_traits = copy.deepcopy(traits)
    traits_modified = False

    # Check metadata
    if full_md:
        for one_md in full_md:
            if 'species' in one_md:
                new_traits['species'] = one_md['species']
                traits_modified = True

    # Check command line parameters
    if args.species is not None:
        new_traits['species'] = args.species
        traits_modified = True

    # Return the appropriate traits
    return new_traits if traits_modified else traits


def calculate_canopycover_masked(pxarray: np.ndarray) -> float:
    """Return greenness percentage of given numpy array of pixels.
    Arguments:
      pxarray (numpy array): rgba image where alpha 255=data and alpha 0=NoData
    Returns:
      (float): greenness percentage
    Notes:
        From TERRA REF canopy cover: https://github.com/terraref/extractors-stereo-rgb/tree/master/canopycover
    """
    total_size = pxarray.shape[0] * pxarray.shape[1]
    nodata = np.count_nonzero(pxarray[:, :, 3] == 0)

    # For masked images, all pixels with rgb>0,0,0 are considered canopy
    data = pxarray[pxarray[:, :, 3] == 255]
    canopy = len(data[np.sum(data[:, 0:3], 1) > 0])
    ratio = canopy/float(total_size - nodata)
    # Scale ratio from 0-1 to 0-100
    ratio *= 100.0

    return ratio


def centroid_as_json(geom: ogr.Geometry) -> str:
    """Return centroid lat/lon of a geojson object.
    Arguments:
        geom: the geometry to get the centroid of
    Return:
        Returns the JSON of the centroid
    """
    centroid = geom.Centroid()
    return centroid.ExportToJson()


def get_plot_species(plot_name: str, full_md: list, args: argparse.Namespace) -> str:
    """Attempts to find the plot name and return its associated species
    Arguments:
        plot_name: the name of the plot to find the species of
        full_md: the full list of metadata
        args: the command line arguments which may have a species override
    Returns:
        Returns the found species or "Unknown" if the plot was not found
    Notes:
        Returns the first match found. If not found, the return value will be one of the following (in
        priority order): the case-insensitive plot name match, the command line species argument, "Unknown"
    """
    possible = None
    optional = None

    # Disable pylint nested block depth check to avoid 2*N looping (save lower case possibility vs. 2 loops
    # with one check in each)
    # pylint: disable=too-many-nested-blocks
    for one_md in full_md:
        if 'species' in one_md:
            optional = one_md['species']
        if 'plots' in one_md:
            for one_plot in one_md['plots']:
                # Try to find the plot name in 'plots' in a case sensitive way, followed by case insensitive
                if 'name' in one_plot:
                    if str(one_plot['name']) == plot_name:
                        if 'species' in one_plot:
                            return one_plot['species']
                    elif str(one_plot['name']).lower() == plot_name.lower():
                        if 'species' in one_plot:
                            possible = one_plot['species']

    # Check if we found a possibility, but not an exact match
    if possible is not None:
        return possible

    return args.species if args.species is not None else optional if optional is not None else "Unknown"


def get_time_stamps(iso_timestamp: str, args: argparse.Namespace) -> list:
    """Returns the date and the local time (offset is stripped) derived from the passed in timestamp
    Args:
        iso_timestamp: the timestamp string
        args: the command line parameters
    Return:
        A list consisting of the date (YYYY-MM-DD) and a local timestamp (YYYY-MM-DDTHH:MM:SS)
    """
    if 'timestamp' in args and args.timestamp:
        timestamp = datetime.datetime.fromisoformat(args.timestamp)
    elif iso_timestamp:
        timestamp = datetime.datetime.fromisoformat(iso_timestamp)
    else:
        return ['', '']

    return [timestamp.strftime('%Y-%m-%d'), timestamp.strftime('%Y-%m-%dT%H:%M:%S')]


class CanopyCover(algorithm.Algorithm):
    """Calculates canopy cover percentage on soil-masked image"""

    @property
    def supported_file_ext(self) -> tuple:
        """Returns a tuple of supported file extensions in lowercase (with the preceding dot: eg '.tif')"""
        return '.tiff', '.tif'

    def add_parameters(self, parser: argparse.ArgumentParser) -> None:
        """Adds parameters
        Arguments:
            parser: instance of argparse
        """
        # pylint: disable=no-self-use
        parser.add_argument('--species', dest="species", type=str, nargs='?',
                            help="name of the species associated with the canopy cover")
        parser.add_argument('--timestamp', help='the timestamp to use in ISO 8601 format (eg:YYYY-MM-DDTHH:MM:SS')

    def check_continue(self, environment: Environment, check_md: dict, transformer_md: list, full_md: list) -> tuple:
        """Checks if conditions are right for continuing processing
        Arguments:
            environment: instance of transformer class
            check_md: dictionary
            transformer_md: dictionary
            full_md: dictionary
        Return:
            Returns a tuple containing the return code for continuing or not, and
            an error message if there's an error
        """
        # pylint: disable=unused-argument
        # Check that we have what we need
        if check_md.get_list_files() is None:
            return -1, "Unable to find list of files associated with this request"

        # Make sure there's a tiff file to process
        image_exts = self.supported_file_ext
        found_file = False
        for one_file in check_md.get_list_files():
            ext = os.path.splitext(one_file)[1]
            if ext and ext in image_exts:
                found_file = True
                break

        # Return the appropriate result
        if found_file:
            return (0,)
        raise FileNotFoundError("Unable to find an image file to work with")

    def perform_process(self, environment: Environment, check_md: CheckMD, transformer_md: dict, full_md: list) -> dict:
        """Performs the processing of the data
        Arguments:
            environment: instance of transformer class
            check_md: dictionary
            transformer_md: dictionary
            full_md: dictionary
        Return:
            Returns a dictionary with the results of processing
        """
        # Disable pylint checks that would reduce readability
        # pylint: disable=unused-argument,too-many-locals,too-many-branches,too-many-statements
        # Setup local variables
        (_, localtime) = get_time_stamps(check_md.timestamp, environment.args)

        save_csv_filename = os.path.join(check_md.working_folder, "canopycover.csv")
        # pylint: disable=consider-using-with
        save_file = open(save_csv_filename, 'w')

        (fields, traits) = get_traits_table()

        # Setup default trait values
        traits = setup_default_traits(traits, environment.args, full_md)

        # Preparing and writing headers
        save_csv_header = ','.join(map(str, fields))
        if save_file:
            save_file.write(save_csv_header + "\n")

        # Loop through finding all image files
        image_exts = self.supported_file_ext
        num_files = 0
        total_plots_calculated = 0
        logging.debug("Looking for images with an extension of: %s", ",".join(image_exts))
        for one_file in check_md.get_list_files():
            ext = os.path.splitext(one_file)[1]
            if not ext or ext not in image_exts:
                logging.debug("Skipping non-supported file '%s'", one_file)
                continue

            image_bounds = geoimage.get_image_bounds(one_file)
            # if not image_bounds:
            #     logging.info("Image file does not appear to be geo-referenced '%s'", one_file)
            #     continue

            overlap_plots = [os.path.basename(os.path.dirname(one_file))]

            num_files += 1
            for plot_name in overlap_plots:

                try:
                    raster = gdal.Open(one_file)
                    pxarray = np.array(raster.ReadAsArray())
                    if pxarray is not None:
                        if len(pxarray.shape) < 3:
                            logging.warning('Unexpected image dimensions for file "%s"', one_file)
                            logging.warning('    expected 3 and received %s', str(pxarray.shape))
                            break

                        # Check if there's an Alpha channel and add it if not
                        if pxarray.shape[0] >= 4:
                            image_to_use = pxarray
                        else:
                            logging.info('Adding missing alpha channel to loaded image from "%s"', one_file)
                            image_to_use = _add_image_mask(one_file) if image_bounds else _add_image_mask_non_geo(pxarray)
                            del pxarray     # Potentially free up memory

                        logging.debug("Calculating canopy cover")
                        cc_val = calculate_canopycover_masked(np.rollaxis(image_to_use, 0, 3))
                        cc_val_str = format(cc_val, '.' + str(SIGNIFICANT_DIGITS) + 'g')

                        # Write the datapoint geographically and otherwise
                        logging.debug("Writing to CSV files")

                        if save_file:
                            traits['canopy_cover'] = cc_val_str
                            traits['species'] = get_plot_species(plot_name, full_md, environment.args)
                            traits['site'] = plot_name
                            traits['local_datetime'] = localtime
                            trait_list = generate_traits_list(traits)
                            csv_data = ','.join(map(str, trait_list))
                            save_file.write(csv_data + "\n")

                        total_plots_calculated += 1

                    else:
                        continue
                except Exception as ex:
                    if logging.getLogger().level == logging.DEBUG:
                        logging.exception("Exception caught while processing canopy")
                    logging.warning("Exception caught while processing canopy cover: %s", str(ex))
                    logging.warning("Error generating canopy cover for '%s'", one_file)
                    logging.warning("    plot name: '%s'", plot_name)
                    continue

        # Check that we got something
        if not num_files:
            return {'code': -1000, 'error': "No files were processed"}
        if not total_plots_calculated:
            return {'code': -1001, 'error': "No images were able to have their canopy cover calculated"}

        # Setup the metadata for returning files
        file_md = []
        if save_file:
            file_md.append({'path': save_csv_filename, 'key': 'csv'})

        # Perform cleanup
        if save_file:
            save_file.close()
            del save_file

        return {'code': 0, 'files': file_md}


if __name__ == "__main__":
    CONFIGURATION = ConfigurationCanopycover()
    entrypoint.entrypoint(CONFIGURATION, CanopyCover())
