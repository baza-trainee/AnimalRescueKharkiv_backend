#!/bin/bash
cd /home/ec2-user/ARK
sudo docker-compose -f compose.yaml --profile backend down
git pull
sudo docker-compose -f compose.yaml --profile backend build
sudo docker-compose -f compose.yaml --profile backend up -d
