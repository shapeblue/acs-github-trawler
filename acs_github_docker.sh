#!/bin/bash

#DOCKER_BUILDKIT=1 docker build --tag=acsn:0.1 . && img=`docker image ls | grep acsn | grep 0.1 | awk '{print $3}'` && docker run -it --entrypoint /bin/bash --env-file ./env.vars $img

echo "Starting Docker Container"
remote_output_dir="`grep  'tmp_dir=' ./env.vars | awk -F '=' '{print $2}'`/dockeroutput"
DOCKER_BUILDKIT=1 docker build --tag=acsn:0.1 . && img=`docker image ls | grep acsn | grep 0.1 | awk '{print $3}'` && docker run -v $PWD/docker_out:/tmp/docker_output --env-file ./env.vars $img
mv $PWD/docker_out/* .
rm -rf $PWD/docker_out
