# Tools for Amterdam HERE project

To clone this repository locally, type:

    git clone https://github.com/bertspaan/ams-here-tools.git

Start Jupyter Notebook from HERE's Docker container:

    cd docker
    ./copy_credentials.sh # You only need to run this command once. Make sure the three required files are present!
    ./docker_build.sh # First, build the Docker container. Run this once, and run this after changing the Dockerfile
    ./docker_run.sh
