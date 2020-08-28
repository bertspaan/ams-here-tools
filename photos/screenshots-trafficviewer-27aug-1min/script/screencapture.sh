#!/usr/bin/env bash
while [ 1 ]; do
  date=$(date +%d\-%m\-%Y\_%H.%M.%S)
  echo $date
  screencapture -t jpg -x ~/Desktop/traffic_screenshots/screenshot-$date.jpg
  sleep 60 
done


