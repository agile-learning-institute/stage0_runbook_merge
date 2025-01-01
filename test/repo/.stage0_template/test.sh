#!/bin/bash

rm -rf ~/tmp/testRepo
cp -r ../* ~/tmp/testRepo

docker run --rm /
    -v ~/tmp/testRepo:/repo 
    -v ./test_data:/specifications 
    -e SERVICE_NAME=order 
    ghcr.io/agile-learning-institute/stage0-generator:latest

