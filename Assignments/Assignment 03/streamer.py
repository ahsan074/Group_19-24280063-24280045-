from pyspark.sql import SparkSession
from pyspark.sql.functions import (from_json, col, window, desc, lag, row_number, to_timestamp)
from pyspark.sql.types import (StructType, StructField, StringType, IntegerType, DoubleType, TimestampType)
from pyspark.sql.window import Window
from prometheus_client import Counter, Gauge, start_http_server

# Start Prometheus HTTP Server
start_http_server(9000)

# Define Prometheus Metrics
traffic_counter = Counter("traffic_volume_total", "Total number of vehicles per sensor", ["sensor_id"])
congestion_counter = Counter("high_congestion_count", "Total high congestion events per sensor", ["sensor_id"])
speed_gauge = Gauge("average_speed", "Average speed per sensor", ["sensor_id"])

# Initialize Spark Session
spark = SparkSession.builder \
    .appName("TrafficMonitoring") \
    .config("spark.rpc.message.maxSize", "512") \
    .getOrCreate()

# Define Kafka Data Schema
traffic_schema = StructType([
    StructField("sensor_id", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("vehicle_count", IntegerType(), True),
    StructField("average_speed", DoubleType(), True),
    StructField("congestion_level", StringType(), True),
])

# Read Streaming Data from Kafka
kafka_stream = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", "localhost:9092")
    .option("subscribe", "traffic_data")
    .option("startingOffsets", "earliest")
    .option("failOnDataLoss", "true")
    .option("maxOffsetsPerTrigger", "50")
    .option("kafka.request.timeout.ms", "60000")
    .option("kafka.metadata.max.age.ms", "60000")
    .load()
    .selectExpr("CAST(value AS STRING)")
)

json_stream = kafka_stream.selectExpr("CAST(value AS STRING) as json_str")
parsed_stream = json_stream.select(from_json(col("json_str"), traffic_schema).alias("data"))
traffic_events = parsed_stream.select("data.*")

# Data Quality Checks
filtered_data = traffic_events.filter(col("sensor_id").isNotNull() & col("timestamp").isNotNull())
filtered_data = filtered_data.filter((col("vehicle_count") >= 0) & (col("average_speed") > 0))
filtered_data = filtered_data.dropDuplicates(["sensor_id", "timestamp"])
filtered_data = filtered_data.withColumn("timestamp", to_timestamp(col("timestamp")))

# Traffic Volume per Sensor (5-minute window)
traffic_agg = (
    filtered_data.withWatermark("timestamp", "5 minutes")
    .groupBy("sensor_id", window(col("timestamp"), "5 minutes"))
    .agg({"vehicle_count": "sum"})
    .withColumnRenamed("sum(vehicle_count)", "total_vehicle_count")
)

# Congestion Hotspots
congestion_agg = (
    filtered_data.withWatermark("timestamp", "5 minutes")
    .filter(col("congestion_level") == "HIGH")
    .groupBy("sensor_id", window(col("timestamp"), "5 minutes"))
    .count()
    .filter(col("count") >= 3)
)

# Average Speed per Sensor
speed_agg = (
    filtered_data.withWatermark("timestamp", "10 minutes")
    .groupBy("sensor_id", window(col("timestamp"), "10 minutes"))
    .agg({"average_speed": "avg"})
    .withColumnRenamed("avg(average_speed)", "avg_speed")
)

# Identify Sudden Speed Drops
speed_window = Window.partitionBy("sensor_id").orderBy("timestamp")
speed_variation = filtered_data.withColumn("prev_speed", lag("average_speed").over(speed_window))
speed_drop = speed_variation.withColumn(
    "drop_percent", (col("prev_speed") - col("average_speed")) / col("prev_speed")
).filter((col("prev_speed").isNotNull()) & (col("drop_percent") >= 0.5))

# Busiest Sensors (30-minute window)
busiest_sensors = (
    filtered_data.withWatermark("timestamp", "30 minutes")
    .groupBy("sensor_id", window(col("timestamp"), "30 minutes"))
    .agg({"vehicle_count": "sum"})
    .withColumnRenamed("sum(vehicle_count)", "total_vehicle_count")
)

# Top 3 Busiest Sensors
ranking_window = Window.partitionBy("window").orderBy(desc("total_vehicle_count"))
top_sensors = busiest_sensors.withColumn("rank", row_number().over(ranking_window)).filter(col("rank") <= 3)

# Functions to Send Metrics to Prometheus

def update_traffic(batch_df, batch_id):
    for row in batch_df.collect():
        traffic_counter.labels(sensor_id=row["sensor_id"]).inc(row["total_vehicle_count"])

def update_congestion(batch_df, batch_id):
    for row in batch_df.collect():
        congestion_counter.labels(sensor_id=row["sensor_id"]).inc(row["count"])

def update_speed(batch_df, batch_id):
    for row in batch_df.collect():
        speed_gauge.labels(sensor_id=row["sensor_id"]).set(row["avg_speed"])

# Stream Data to Prometheus
traffic_agg.writeStream.foreachBatch(update_traffic).outputMode("update").start()
congestion_agg.writeStream.foreachBatch(update_congestion).outputMode("update").start()
speed_agg.writeStream.foreachBatch(update_speed).outputMode("update").start()

# Send Traffic Volume Data to Kafka
output_stream = traffic_agg.selectExpr("to_json(struct(sensor_id, window, total_vehicle_count)) as value")
query_kafka = (
    output_stream.writeStream.format("kafka")
    .option("kafka.bootstrap.servers", "localhost:9092")
    .option("topic", "traffic_analysis")
    .option("checkpointLocation", "/tmp/spark_checkpoint_traffic_volume")
    .outputMode("update")
    .start()
)

# Print Traffic Volume to Console
query_console = (
    traffic_agg.writeStream.format("console")
    .option("truncate", "false")
    .outputMode("update")
    .start()
)

query_kafka.awaitTermination()
query_console.awaitTermination()
