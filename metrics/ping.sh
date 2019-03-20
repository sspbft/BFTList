ping -c 5 $1 | tail -1 | awk '{print $4}' | tr '/' ' ' | awk '{print $2}'
