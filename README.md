# Tools for Amterdam HERE project

To clone this repository locally, type:

    git clone https://github.com/bertspaan/ams-here-tools.git

## Run Jupyter Notebook from HERE's Docker container

Some of the files used in this repository come from HERE's [SDK for Python Setup Guide](https://developer.here.com/documentation/sdk-python/dev_guide/topics/docker/home.html).

The [Dockerfile](https://docs.docker.com/engine/reference/builder/) and the files required to build the Docker container are found in the [`python-sdk`](python-sdk) directory:

    cd python-sdk

First, you need [three credentials files](https://developer.here.com/documentation/sdk-python/dev_guide/topics/credentials.html) from the HERE platform.

Copy them to this directory by running:

    ./copy_credentials.sh

Then, build the Docker container:

    ./docker_build.sh

Run the Docker container:

    ./docker_run.sh

Jupyter Notebook is now running on [http://localhost:8080/](http://localhost:8080/).

Notebook files in the [`python-sdk/notebooks`](python-sdk/notebooks) directory will be available in http://localhost:8080/tree/host-notebooks.
