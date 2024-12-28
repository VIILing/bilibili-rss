#!/bin/bash
source ~/.bashrc

script_path=$(realpath "$0")
dir_path=$(dirname "$script_path")

commitId=$(git rev-parse --short HEAD)
sudo docker build -t VIILing/bilibili-rss:"$commitId" -t VIILing/bilibili-rss:dev "$dir_path"