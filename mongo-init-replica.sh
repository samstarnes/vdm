#!/bin/bash
# set -e

# Wait for MongoDB to start
until mongo --host ytdldb --port 56001 --eval "print(\"waiting for mongodb\")"
do
    sleep 1
done

# Initiate replica set
echo "Initiating replica set..."
mongo --host ytdldb --port 56001 <<EOF
rs.initiate({
    _id: "rs0",
    members: [
        { _id: 0, host: "ytdldb:56001" }
    ]
})
EOF

echo "Replica set initiated successfully."
