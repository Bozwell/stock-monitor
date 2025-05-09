#!/usr/bin/env bash

# git pull
git pull

# remove container 
docker rm $(docker stop stock-monitor-container)

# build docker image
docker build -t stock-monitor .

# run
docker run -d --tty --name stock-monitor-container --memory=1g  -e TZ=Asia/Seoul -v $(pwd)/config:/app/config stock-monitor

# config autostart
docker update --restart unless-stopped stock-monitor-container

# remove old docker image
docker image prune -f

# check status
docker ps
