#!/bin/sh
rclone copy $1/$2 gd:VODS/$(basename $1)/$2 --progress