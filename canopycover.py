#!/usr/bin/env python3
"""Calculates canopy coverage for plots in georeferenced images
"""

import argparse
import copy
import json
import logging
import os
from typing import Union
import numpy as np
import dateutil.parser
from agpypeline import entrypoint, algorithm, geoimage
from agpypeline.environment import Environment
from osgeo import gdal, ogr

from configuration import ConfigurationCanopycover


# Array of trait names that should have array values associated with them
TRAIT_NAME_ARRAY_VALUE = ['canopy_cover', 'site']

# Mapping of default trait names to fixed values
TRAIT_NAME_MAP = {
    'access_level': '2',
    'species': 'Unknown',
    'citation_author': '"Zongyang, Li"',
    'citation_year': '2016',
    'citation_title': 'Maricopa Field Station Data and Metadata',
    'method': 'Green Canopy Cover Estimation from Field Scanner RGB images'
}


def get_fields() -> list:
    """Returns the supported field names as a list
    """
    return ['local_datetime', 'canopy_cover', 'access_level', 'species', 'site',
            'citation_author', 'citation_year', 'citation_title', 'method']


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


def generate_traits_list(traits: list) -> list:
    """Returns an array of trait values

    Args:
        traits(dict): contains the set of trait values to return

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
            if 'germplasmName' in one_md:
                new_traits['species'] = one_md['germplasmName']
                traits_modified = True

    # Check command line parameters
    if args.germplasmName is not None:
        new_traits['species'] = args.germplasmName
        traits_modified = True
    if args.citationAuthor is not None:
        new_traits['citation_author'] = args.citationAuthor
        traits_modified = True
    if args.citationTitle is not None:
        new_traits['citation_title'] = args.citationTitle
        traits_modified = True
    if args.citationYear is not None:
        new_traits['citation_year'] = args.citationYear
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
    # If > 75% is NoData, return a -1 ccvalue for omission later
    total_size = pxarray.shape[0] * pxarray.shape[1]
    nodata = np.count_nonzero(pxarray[:, :, 3] == 0)
    nodata_ratio = nodata/float(total_size)
    if nodata_ratio > 0.75:
        return -1

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
        parser.add_argument('--citation_author', dest="citationAuthor", type=str, nargs='?',
                            help="author of citation to use when generating measurements")

        parser.add_argument('--citation_title', dest="citationTitle", type=str, nargs='?',
                            help="title of the citation to use when generating measurements")

        parser.add_argument('--citation_year', dest="citationYear", type=str, nargs='?',
                            help="year of citation to use when generating measurements")

        parser.add_argument('--germplasm_name', dest="germplasmName", type=str, nargs='?',
                            help="name of the germplasm associated with the canopy cover")

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
        if 'list_files' not in check_md:
            return -1, "Unable to find list of files associated with this request"

        # Make sure there's a tiff file to process
        image_exts = self.supported_file_ext
        found_file = False
        for one_file in check_md['list_files']():
            ext = os.path.splitext(one_file)[1]
            if ext and ext in image_exts:
                found_file = True
                break

        # Return the appropriate result
        if found_file:
            return (0,)
        raise FileNotFoundError("Unable to find an image file to work with")

    def perform_process(self, environment: Environment, check_md: dict, transformer_md: dict, full_md: list) -> dict:
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
        timestamp = dateutil.parser.parse(check_md['timestamp'])
        datestamp = timestamp.strftime("%Y-%m-%d")
        localtime = timestamp.strftime("%Y-%m-%dT%H:%M:%S")

        geo_csv_filename = os.path.join(check_md['working_folder'], "canopycover_geostreams.csv")
        bety_csv_filename = os.path.join(check_md['working_folder'], "canopycover.csv")
        geo_file = open(geo_csv_filename, 'w')
        bety_file = open(bety_csv_filename, 'w')

        (fields, traits) = get_traits_table()

        # Setup default trait values
        traits['citation_year'] = timestamp.year
        traits = setup_default_traits(traits, environment.args, full_md)

        # Preparing and writing headers
        geo_csv_header = ','.join(['site', 'trait', 'lat', 'lon', 'dp_time',
                                   'source', 'value', 'timestamp'])
        bety_csv_header = ','.join(map(str, fields))
        if geo_file:
            geo_file.write(geo_csv_header + "\n")
        if bety_file:
            bety_file.write(bety_csv_header + "\n")

        # Loop through finding all image files
        image_exts = self.supported_file_ext
        num_files = 0
        total_plots_calculated = 0
        logging.debug("Looking for images with an extension of: %s", ",".join(image_exts))
        for one_file in check_md['list_files']():
            ext = os.path.splitext(one_file)[1]
            if not ext or ext not in image_exts:
                logging.debug("Skipping non-supported file '%s'", one_file)
                continue

            image_bounds = geoimage.get_image_bounds(one_file)
            if not image_bounds:
                logging.info("Image file does not appear to be geo-referenced '%s'", one_file)
                continue

            overlap_plots = [os.path.basename(os.path.dirname(one_file))]

            num_files += 1
            for plot_name in overlap_plots:
                centroid = json.loads(centroid_as_json(image_bounds))["coordinates"]

                try:
                    raster = gdal.Open(one_file)
                    pxarray = np.array(raster.ReadAsArray())
                    if pxarray is not None:
                        if len(pxarray.shape) < 3:
                            logging.warning('Unexpected image dimensions for file "%s"', one_file)
                            logging.warning('    expected 3 and received %s', str(pxarray.shape))
                            break

                        # Check if there's an Alpha channel and add it if not
                        if len(pxarray.shape) >= 4:
                            image_to_use = pxarray
                        else:
                            logging.info('Adding missing alpha channel to loaded image from "%s"', one_file)
                            mask = np.where(np.sum(pxarray, axis=0) == 0, 0, 255).astype(pxarray.dtype)
                            image_to_use = np.stack((pxarray[0], pxarray[1], pxarray[2], mask))
                            del pxarray     # Potentially free up memory

                        logging.debug("Calculating canopy cover")
                        cc_val = calculate_canopycover_masked(np.rollaxis(image_to_use, 0, 3))

                        # Write the datapoint geographically and otherwise
                        logging.debug("Writing to CSV files")
                        if geo_file:
                            csv_data = ','.join([plot_name,
                                                 'Canopy Cover',
                                                 str(centroid[1]),
                                                 str(centroid[0]),
                                                 localtime,
                                                 one_file,
                                                 str(cc_val),
                                                 datestamp])
                            geo_file.write(csv_data + "\n")

                        if bety_file:
                            traits['canopy_cover'] = str(cc_val)
                            traits['site'] = plot_name
                            traits['local_datetime'] = localtime
                            trait_list = generate_traits_list(traits)
                            csv_data = ','.join(map(str, trait_list))
                            bety_file.write(csv_data + "\n")

                        total_plots_calculated += 1

                    else:
                        continue
                except Exception as ex:
                    logging.warning("Exception caught while processing canopy cover: %s", str(ex))
                    logging.warning("Error generating canopy cover for '%s'", one_file)
                    logging.warning("    plot name: '%s'", plot_name)
                    continue

        # Check that we got something
        if not num_files:
            return {'code': -1000, 'error': "No files were processed"}
        if not total_plots_calculated:
            return {'code': -1001, 'error': "No plots intersected with the images provided"}

        # Setup the metadata for returning files
        file_md = []
        if geo_file:
            file_md.append({'path': geo_csv_filename, 'key': 'csv'})
        if bety_file:
            file_md.append({'path': bety_csv_filename, 'key': 'csv'})

        # Perform cleanup
        if geo_file:
            geo_file.close()
            del geo_file
        if bety_file:
            bety_file.close()
            del bety_file

        return {'code': 0, 'files': file_md}


if __name__ == "__main__":
    CONFIGURATION = ConfigurationCanopycover()
    entrypoint.entrypoint(CONFIGURATION, CanopyCover())
