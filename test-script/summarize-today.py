import influxdb_client
from datetime import datetime, timedelta
from pytz import timezone
from configobj import ConfigObj

config = ConfigObj("pvoutput.conf")
bucket = config['INFLUX_BUCKET']
org = config['INFLUX_ORG']
token = config['INFLUX_TOKEN']
# Store the URL of your InfluxDB instance
url=config['INFLUX_URL']

client = influxdb_client.InfluxDBClient(
    url=url,
    token=token,
    org=org
)


localTz = timezone('america/Sao_Paulo')
utcTz = timezone('UTC')

# Locatime
localNow = datetime.now(localTz)

startTime = localNow.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(utcTz)
endTime = localNow.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(utcTz)

p = {
    "_start" : startTime,
    "_end" : endTime,
    "_every": timedelta(minutes=5)
}

query = '''m_pwr_vdc = from(bucket: "power_plant")\
|> range(start: _start, stop: _end)\
|> filter(fn: (r) => r["name"] == "Inverter" and r["_measurement"] == "modbus" and r["type"] == "input_register") \
|> filter(fn: (r) => r["_field"] == "power_output" or r["_field"] == "Vdc1" or r["_field"] == "Vac" or r["_field"] == "temperature") \
|> aggregateWindow(every: _every, fn: mean, createEmpty: false) \
|> pivot(columnKey:["_field"], rowKey:["_time"], valueColumn:"_value") \
etoday = from(bucket: "power_plant") \
|> range(start: _start, stop: _end)\
|> filter(fn: (r) => r["name"] == "Inverter" and r["_measurement"] == "modbus" and r["type"] == "input_register") \
|> filter(fn: (r) => r["_field"] == "energy_today" or r["_field"] == "energy_total") \
|> aggregateWindow(every: _every, fn: max, createEmpty: false) \
|> pivot(columnKey:["_field"], rowKey:["_time"], valueColumn:"_value") \
join(tables: {etoday: etoday, pwr_vdc: m_pwr_vdc}, on: ["_time", "name", "_measurement", "type", "_start",  "_stop"]) \
|> sort(columns: ["_time"]) \
'''

result = client.query_api().query(query=query, params=p)

results = []
for table in result:
    for record in table.records:
        print(record["_time"].astimezone(localTz).strftime('%H:%M') + ',' +
              str(record["power_output"]) + ',' +
              str(record["energy_today"]) + ',' +
              str(record["Vac"]) + ',' +
              str(record["Vdc1"]) + ',' +
              str(record["energy_total"]*1000) + ',' +
              str(record["temperature"])
              )
