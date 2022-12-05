export $(grep -v '^#' .env | xargs -d '\n') > /dev/null 2>&1
rclone copy $1/$2 $remote/$1/$2 --progress