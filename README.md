# Transformer Canopy Cover

Calculates canopy cover (the percentage pixels identified as a plant) on a plot level for one or more images that have been processed by the [soilmask transformer](https://github.com/AgPipeline/transformer-soilmask) to mask the soil.

## Authors

* Zongyang Li, Donald Danforth Plant Science Center, St. Louis, MO
* Maxwell Burnette, National Supercomputing Applications, Urbana, Il
* Robert Pless, George Washington University, Washington, DC
* Chris Schnaufer, University of Arizona, Tucson, AZ

## Overview

This Transformer processes a soil mask image and generates values of plot-level percent canopy cover traits. From a mask, it generates a scalar value representing the percent of the image that is plant. 

The output is a csv file that can optionally be inserted into the BETYdb database.

## Algorithm description

The core idea of this transformer is to compute the percent of area that is identified as plant in a segmented image.
https://github.com/AgPipeline/transformer-soilmask/blob/master/README.md

## Use 

### Sample Docker Command line

Below is a sample command line that shows how the canopy cover Docker image could be run.
An explanation of the command line options used follows.
Be sure to read up on the [docker run](https://docs.docker.com/engine/reference/run/) command line for more information.

```docker run --rm --mount "src=/home/test,target=/mnt,type=bind" -e "BETYDB_URL=https://terraref.ncsa.illinois.edu/bety/" -e "BETYDB_KEY=<key value>" agpipeline/canopycover:3.0 --working_space "/mnt" --metadata "/mnt/08f445ef-b8f9-421a-acf1-8b8c206c1bb8_metadata.json" --citation_author "Me Myself" --citation_title "Something in the green" --citation_year "2019" --germplasm_name "Big Plant" "/mnt/rgb_mask_L2_my-site_2018-10-01__14-20-40_mask.tif"```

This example command line assumes the source files are located in the `/home/test` folder of the local machine.
The name of the image to run is `agpipeline/canopycover:3.0`.

We are using the same folder for the source metadata and the cleaned metadata.
By using multiple `--mount` options, the source and output files can be separated.

**Docker commands** \
Everything between 'docker' and the name of the image are docker commands.

- `run` indicates we want to run an image
- `--rm` automatically delete the image instance after it's run
- `--mount "src=/home/test,target=/mnt,type=bind"` mounts the `/home/test` folder to the `/mnt` folder of the running image
- `-e "BETYDB_URL=https://terraref.ncsa.illinois.edu/bety/"` the URL to the BETYdb instance to fetch plot boundaries, and other data, from
- `-e "BETYDB_KEY=<key value>"` the key associated with the BETYdb URL (replace `<key value>` with value of your key)

We mount the `/home/test` folder to the running image to make available the file to the software in the image.

**Image's commands** \
The command line parameters after the image name are passed to the software inside the image.
Note that the paths provided are relative to the running image (see the --mount option specified above).

- `--working_space "/mnt"` specifies the folder to use as a workspace
- `--metadata "/mnt/08f445ef-b8f9-421a-acf1-8b8c206c1bb8_metadata.json"` is the name of the source metadata to be cleaned
- `--citation_author "<author name>"` the name of the author to cite in the resulting CSV file(s)
- `--citation_title "<title>"` the title of the citation to store in the resulting CSV file(s)
- `--citation_year "<year>"` the year of the citation to store in the resulting CSV file(s)
- `"/mnt/rgb_mask_L2_my-site_2018-10-01__14-20-40_mask.tif"` the names of one or more image files to use when calculating plot-level canopy cover
