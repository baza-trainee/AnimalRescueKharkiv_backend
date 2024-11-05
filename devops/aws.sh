#!/bin/bash
cd /home/ec2-user/ARK
docker-compose -f compose.yaml --profile backend down
git pull
docker-compose -f compose.yaml --profile backend build
docker-compose -f compose.yaml --profile backend up -d
