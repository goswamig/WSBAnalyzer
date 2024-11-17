# reset_db.sh
#!/bin/bash

echo "Stopping containers..."
docker-compose down

echo "Removing InfluxDB volumes..."
docker volume rm stock-briefing_influxdb-data
docker volume rm stock-briefing_influxdb-config

docker-compose rm -rf
docker rmi wsb-analyzer
docker rmi influxdb

docker volume rm stock-briefing_influxdb-data
docker volume rm stock-briefing_influxdb-config


# lets rebuild the docker image
docker-compose build wsb-analyzer

docker-compose up -d 


echo "Waiting for InfluxDB to initialize..."
sleep 10

echo "Checking InfluxDB logs..."
docker logs influxdb


echo "Checking if wsb-analyzer container is running..."
docker ps | grep wsb-analyzer
docker logs wsb-analyzer


# lets tail the logs
docker-compose logs -f wsb-analyzer


# echo "Running token verification..."
# python src/verify_token.py

# echo "Running setup verification..."
# python src/verify_setup.py