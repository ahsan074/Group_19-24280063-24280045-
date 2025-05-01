from kafka import KafkaProducer
import json
import time
import random
from datetime import datetime

#Prometheus HTTP Server on port 9000
#start_http_server(9000)

# Kafka Configuration
KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC = "traffic_data"

# Create Kafka Producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# Define Sensor Locations
sensors = ["sensor_1", "sensor_2", "sensor_3", "sensor_4", "sensor_5"]


while True:
    data = {
        "sensor_id": random.choice(sensors),
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "vehicle_count": random.randint(0, 50),
        "average_speed": round(random.uniform(20, 80), 2),
        "congestion_level": random.choice(["LOW", "MEDIUM", "HIGH"])
    }
    
    # Send Data to Kafka Topic
    producer.send(KAFKA_TOPIC, data)
    print(f"Sent: {data}")
    time.sleep(2) 
