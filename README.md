# Transformer Canopy Cover

Calculates canopy cover (the percentage pixels identified as a plant) on a plot level for one or more images that have been processed by the [soilmask transformer](https://github.com/AgPipeline/transformer-soilmask) to mask the soil.

## Authors

* Zongyang Li, Donald Danforth Plant Science Center, St. Louis, MO
* Maxwell Burnette, National Supercomputing Applications, Urbana, Il
* Robert Pless, George Washington University, Washington, DC
* Chris Schnaufer, University of Arizona, Tucson, AZ

## Overview

This Transformer processes a soil mask image and generates a value of plot-level percent canopy cover. This is a scalar value representing the percent of the image mask that is classified as plant. 

The output is a csv file that can optionally be inserted into the BETYdb database.

## Algorithm description

The core idea of this transformer is to compute the percent of area that is identified as plant in a segmented image.
These masked images can be generated by the [soilmask transformer](https://github.com/AgPipeline/transformer-soilmask/blob/master/README.md) or similar algorithm.

This algorithm expects a one-layer geotiff file with the extention .tif or .tiff. See https://drive.google.com/file/d/1xWRU0YgK3Y9aUy5TdRxj14gmjLlozGxo/view for an example. 

## Use 

### Sample Docker Command line

First build the Docker image, using the Dockerfile, and tag it agdrone/transformer-canopycover:1.1. 
Read about the [docker build](https://docs.docker.com/engine/reference/commandline/build/) command if needed.

```bash
docker build -t agdrone/transformer-canopycover:1.1 ./
```

Below is a sample command line that shows how the canopy cover Docker image could be run.
An explanation of the command line options used follows.
Be sure to read up on the [docker run](https://docs.docker.com/engine/reference/run/) command line for more information.

```bash
docker run --rm --mount "src=${PWD}/test_data,target=/mnt,type=bind" agdrone/transformer-canopycover:1.1 --working_space "/mnt" --metadata "/mnt/experiment.yaml" --citation_author "Me Myself" --citation_title "Something in the green" --citation_year "2019" --germplasm_name "Big Plant" "/mnt/rgb_1_2_E.tif"
```

This example command line assumes the source files are located in the `test_data` folder off the current folder.
The name of the image to run is `agdrone/transformer-canopycover:1.1`.

We are using the same folder for the source metadata and the cleaned metadata.
By using multiple `--mount` options, the source and output files can be separated.

**Docker commands** \
Everything between 'docker' and the name of the image are docker commands.

- `run` indicates we want to run an image
- `--rm` automatically delete the image instance after it's run
- `--mount "src=${PWD}/test_data,target=/mnt,type=bind"` mounts the `${PWD}/test` folder to the `/mnt` folder of the running image

We mount the `${PWD}/test` folder to the running image to make available the file to the software in the image.

**Image's commands** \
The command line parameters after the image name are passed to the software inside the image.
Note that the paths provided are relative to the running image (see the --mount option specified above).

- `--working_space "/mnt"` specifies the folder to use as a workspace
- `--metadata "/mnt/experiment.yaml"` is the name of the source metadata to be cleaned
- `--citation_author "Me Myself"` the name of the author to cite in the resulting CSV file(s)
- `--citation_title "Something in the green"` the title of the citation to store in the resulting CSV file(s)
- `--citation_year "2019"` the year of the citation to store in the resulting CSV file(s)
- `"mnt/rgb_1_2_E.tif"` the names of one or more image files to use when calculating plot-level canopy cover

**Testing the Docker Transformer** \
In order to make sure that the canopy cover transformer is functioning correctly, create an image that is all black
using an image editor such as [gimp](https://www.gimp.org) and export the result to the working directory as a .tif or .tiff file.
Move this file to the project directory and then using the above docker run command, make sure that -1 is returned. Doing the same
with a completely white image, make sure that 0 is returned. 

The reason this should be done is in order to test the extremes for image data.

Next test on these [sample plot images](https://drive.google.com/file/d/1xWRU0YgK3Y9aUy5TdRxj14gmjLlozGxo/view) and make sure
that reasonable values are returned.

**Deploying the Transformer** \
Once you have used the transformer on your image data, you can upload your docker image to [Docker Hub](https://hub.docker.com)
so that it can be accessed remotely. Use a tutorial such as [this one](https://ropenscilabs.github.io/r-docker-tutorial/04-Dockerhub.html)
in order to upload your image to Docker Hub

## Acceptance Testing

There are automated test suites that are run via [GitHub Actions](https://docs.github.com/en/actions).
In this section we provide details on these tests so that they can be run locally as well.

These tests are run when a [Pull Request](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-requests) or [push](https://docs.github.com/en/github/using-git/pushing-commits-to-a-remote-repository) occurs on the `develop` or `master` branches.
There may be other instances when these tests are automatically run, but these are considered the mandatory events and branches.

### PyLint and PyTest

These tests are run against any Python scripts that are in the repository.

[PyLint](https://www.pylint.org/) is used to both check that Python code conforms to the recommended coding style, and checks for syntax errors.
The default behavior of PyLint is modified by the `pylint.rc` file in the [Organization-info](https://github.com/AgPipeline/Organization-info) repository.
Please also refer to our [Coding Standards](https://github.com/AgPipeline/Organization-info#python) for information on how we use [pylint](https://www.pylint.org/).

The following command can be used to fetch the `pylint.rc` file:
```bash
wget https://raw.githubusercontent.com/AgPipeline/Organization-info/master/pylint.rc
```

Assuming the `pylint.rc` file is in the current folder, the following command can be used against the `canopycover.py` file:
```bash
# Assumes Python3.7+ is default Python version
python -m pylint --rcfile ./pylint.rc canopycover.py
``` 

In the `tests` folder there are testing scripts and their supporting files.
The tests are designed to be run with [Pytest](https://docs.pytest.org/en/stable/).
When running the tests, the root of the repository is expected to be the starting directory.

The command line for running the tests is as follows:
```bash
# Assumes Python3.7+ is default Python version
python -m pytest -rpP
```

If [pytest-cov](https://pytest-cov.readthedocs.io/en/latest/) is installed, it can be used to generate a code coverage report as part of running PyTest.
The code coverage report shows how much of the code has been tested; it doesn't indicate **how well** that code has been tested.
The modified PyTest command line including coverage is:
```bash
# Assumes Python3.7+ is default Python version
python -m pytest --cov=. -rpP 
```

### Docker Testing

The Docker testing Workflow replicate the examples in this document to ensure they continue to work.
