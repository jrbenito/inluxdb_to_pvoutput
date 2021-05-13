import influxdb_client
from datetime import datetime, timedelta
from pytz import timezone
from configobj import ConfigObj

config = ConfigObj("src/conf/pvoutput.conf")
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
    "_every": timedelta(seconds=300)
}

query = '''m_pwr_vdc = from(bucket: "power_plant")\
    |> range(start: _start, stop: _end)\
    |> filter(fn: (r) => r["_measurement"] == "modbus" and r["type"] == "input_register") \
    |> filter(fn: (r) => r["_field"] == "power_output" or r["_field"] == "power_input" or r["_field"] == "Vdc1" or r["_field"] == "Vac" or r["_field"] == "temperature" or r["_field"] == "system_power_total") \
    |> drop(columns: ["name", "type"])
    |> aggregateWindow(every: _every, fn: mean, createEmpty: false) \
    |> pivot(columnKey:["_field"], rowKey:["_time"], valueColumn:"_value") \
    etoday = from(bucket: "power_plant") \
    |> range(start: _start, stop: _end)\
    |> filter(fn: (r) => r["_measurement"] == "modbus" and r["type"] == "input_register") \
    |> filter(fn: (r) => r["_field"] == "energy_today" or r["_field"] == "energy_total" or r["_field"] == "Wh_export_since_reset") \
    |> drop(columns: ["name", "type"])
    |> aggregateWindow(every: _every, fn: max, createEmpty: false) \
    |> pivot(columnKey:["_field"], rowKey:["_time"], valueColumn:"_value") \
    join(tables: {etoday: etoday, pwr_vdc: m_pwr_vdc}, on: ["_time", "_start",  "_stop"]) \
    |> sort(columns: ["_time"]) \
    '''

result = client.query_api().query(query=query, params=p)

results = []
for table in result:
    for record in table.records:
        pwout = record["power_output"]
        pwnet = record["system_power_total"] if record["system_power_total"] is not None else 0
        consumption = pwout + pwnet if pwout is not None else pwnet
        record['consumption'] = None
        if consumption > 0: 
            record['consumption'] = consumption
        if (record["power_output"] is None) and (record['consumption'] is not None):
            record["power_output"] = 0
            record["energy_today"] = 0
        if record["system_power_total"] is None:
            record["system_power_total"] = ''
        print(record["_time"].astimezone(localTz).strftime('%H:%M') + ',' +
              str(record["power_output"]) + ',' +
              str(record["energy_today"]) + ',' +
              str(record["Vac"]) + ',' +
              str(record["Vdc1"]) + ',' +
              str(record["energy_total"]) + ',' +
              str(record["temperature"]) + ',' +
              str(record['consumption'])
              )
