#!/usr/bin/env bash

docker run -p 8080:8080 -p 8998:8998 \
  -v $(pwd)/notebooks:/usr/local/envs/olp-sdk-for-python-1.5-env/olp-sdk-for-python-1.5/host-notebooks \
  -it olp-sdk-for-python-1.5
