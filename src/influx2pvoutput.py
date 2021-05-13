import sys
import requests
import influxdb_client
from time import sleep, time
from datetime import datetime, timedelta
from pytz import timezone
from configobj import ConfigObj
from collections import defaultdict

# read settings from config file                                                                                                                               
config = ConfigObj("conf/pvoutput.conf")
SYSTEMID = config['SYSTEMID']
APIKEY = config['APIKEY']

INFLUX_BUCKET = config['INFLUX_BUCKET']
INFLUX_ORG = config['INFLUX_ORG']
INFLUX_TOKEN = config['INFLUX_TOKEN']
INFLUX_URL = config['INFLUX_URL']

LOCAL_TZ = timezone(config['TIME_ZONE'])
UTC_TZ = timezone('UTC')

WH_IN_KWH = 1000

class PVOutputAPI(object):

    def __init__(self, API, system_id=None):
        self._API = API
        self._systemID = system_id
        self._wh_today_last = 0

    def add_status(self, payload, system_id=None):
        """Add live output data. Data should contain the parameters as described
        here: http://pvoutput.org/help.html#api-addstatus ."""
        sys_id = system_id if system_id is not None else self._systemID
        self.__call("https://pvoutput.org/service/r2/addstatus.jsp", payload, sys_id)

    def add_output(self, payload, system_id=None):
        """Add end of day output information. Data should be a dictionary with
        parameters as described here: http://pvoutput.org/help.html#api-addoutput ."""
        sys_id = system_id if system_id is not None else self._systemID
        self.__call("http://pvoutput.org/service/r2/addoutput.jsp", payload, sys_id)

    def __call(self, url, payload, system_id=None):
        headers = {
            'X-Pvoutput-Apikey': self._API,
            'X-Pvoutput-SystemId': system_id,
            'X-Rate-Limit': '1'
        }

        # Make tree attempts
        for i in range(3):
            try:
                r = requests.post(url, headers=headers, data=payload, timeout=10)
                reset = round(float(r.headers['X-Rate-Limit-Reset']) - time())
                if int(r.headers['X-Rate-Limit-Remaining']) < 10:
                    print("Only {} requests left, reset after {} seconds".format(
                        r.headers['X-Rate-Limit-Remaining'],
                        reset))
                if r.status_code == 403:
                    print("Forbidden: " + r.reason)
                    sleep(reset + 1)
                else:
                    r.raise_for_status()
                    break
            except requests.exceptions.HTTPError as errh:
                print(localnow().strftime('%Y-%m-%d %H:%M'), " Http Error:", errh, " with content:", r.content)
            except requests.exceptions.ConnectionError as errc:
                print(localnow().strftime('%Y-%m-%d %H:%M'), "Error Connecting:", errc, " with content:", r.content)
            except requests.exceptions.Timeout as errt:
                print(localnow().strftime('%Y-%m-%d %H:%M'), "Timeout Error:", errt, " with content:", r.content)
            except requests.exceptions.RequestException as err:
                print(localnow().strftime('%Y-%m-%d %H:%M'), "OOps: Something Else", err, " with content:", r.content)

            sleep(5)
        else:
            print(localnow().strftime('%Y-%m-%d %H:%M'),
                  "Failed to call PVOutput API after {} attempts.".format(i))

    def send_status(self, date, energy_gen=None, power_gen=None, energy_imp=None,
                    power_imp=None, temp=None, vdc=None, cumulative=False, vac=None,
                    temp_inv=None, energy_life=None, comments=None, power_vdc=None,
                    system_id=None):
        # format status payload
        payload = {
            'd': date.strftime('%Y%m%d'),
            't': date.strftime('%H:%M'),
        }

        # Only report total energy if it has changed since last upload
        # this trick avoids avg power to zero with inverter that reports
        # generation in 100 watts increments (Growatt and Canadian solar)
        if ((energy_gen is not None) and (self._wh_today_last != energy_gen)):
            self._wh_today_last = int(energy_gen)
            payload['v1'] = int(energy_gen)

        if power_gen is not None:
            payload['v2'] = float(power_gen)
        if energy_imp is not None:
            payload['v3'] = int(energy_imp)
        if power_imp is not None:
            payload['v4'] = float(power_imp)
        if temp is not None:
            payload['v5'] = float(temp)
        if vdc is not None:
            payload['v6'] = float(vdc)
        if cumulative is True:
            payload['c1'] = 1
        else:
            payload['c1'] = 0
        if vac is not None:
            payload['v8'] = float(vac)
        if temp_inv is not None:
            payload['v9'] = float(temp_inv)
        if energy_life is not None:
            payload['v10'] = int(energy_life)
        if comments is not None:
            payload['m1'] = str(comments)[:30]
        # calculate efficiency
        if ((power_vdc is not None) and (power_vdc > 0) and (power_gen is not None)):
            payload['v12'] = (float(power_gen) / float(power_vdc)) * 100

        # Send status
        self.add_status(payload, system_id)

# Local time with timezone
def localnow():
    return datetime.now(LOCAL_TZ)

# Query influxdb for data
def get_data():

    endTime = localnow().replace(second=0, microsecond=0).astimezone(UTC_TZ)
    startTime = endTime - timedelta(seconds=300) # 5m before
    

    p = {
        "_start" : startTime,
        "_end" : endTime,
        "_every": timedelta(minutes=5)
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

    result = influx.query_api().query_stream(query=query, params=p)

    return result


# Aplication loop
def main_loop():
    

    # Loop until end of universe
    while True:
        records = get_data()
        for rec in records:
            record = defaultdict(lambda: None, rec.values)
            record["energy_today"] = record["energy_today"] * WH_IN_KWH if record["energy_today"] is not None else None
            # calculate consumption
            pwout = record["power_output"] if record["power_output"] is not None else 0
            pwnet = record["system_power_total"] if record["system_power_total"] is not None else 0
            consumption = pwout + pwnet
            if consumption > 0:
                record['consumption'] = consumption

            print(record)
            pvo.send_status(date=record["_time"].astimezone(LOCAL_TZ), energy_gen=record["energy_today"],
                            power_gen=record["power_output"], vdc=record["Vdc1"],
                            vac=record["Vac"], temp_inv=record["temperature"],
                            energy_life=record["energy_total"], power_vdc=record["power_input"], power_imp=record["consumption"])
            # sleep until next multiple of 5 minutes

        min = 5 - localnow().minute % 5
        sleep(min*60 - localnow().second)
        
# Main entrypoint
if __name__ == '__main__':
    try:
        # init
        pvo = PVOutputAPI(APIKEY, SYSTEMID)
        influx = influxdb_client.InfluxDBClient(
            url=INFLUX_URL,
            token=INFLUX_TOKEN,
            org=INFLUX_ORG
        )

        # execute
        print('Starting: ', localnow())
        main_loop()
    except KeyboardInterrupt:
        print('\nExiting by user request.\n', file=sys.stderr)
        sys.exit(0)