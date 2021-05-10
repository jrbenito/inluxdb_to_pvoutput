import sys
import requests
from time import sleep, time
from datetime import datetime
from pytz import timezone
from configobj import ConfigObj

# read settings from config file                                                                                                                               
config = ConfigObj("pvoutput.conf")
SYSTEMID = config['SYSTEMID']
APIKEY = config['APIKEY']

INFLUX_BUCKET = config['INFLUX_BUCKET']
INFLUX_ORG = config['INFLUX_ORG']
INFLUX_TOKEN = config['INFLUX_TOKEN']
INFLUX_URL = config['INFLUX_URL']

LOCAL_TZ = timezone(config['TIME_ZONE'])

# Local time with timezone
def localnow():
    return datetime.now(LOCAL_TZ)

# Aplication loop
def main_loop():
    # init
    #pvo = PVOutputAPI(APIKEY, SYSTEMID)

    # Loop until end of universe
    while True:
        
        if True:
            # pvo.send_status(date=inv.date, energy_gen=inv.wh_today,
            #                 power_gen=inv.ac_power, vdc=inv.pv_volts,
            #                 vac=inv.ac_volts, temp=temp,
            #                 temp_inv=inv.temp, energy_life=inv.wh_total,
            #                 power_vdc=inv.pv_power)
            # sleep until next multiple of 5 minutes
            min = 5 - localnow().minute % 5
            sleep(min*60 - localnow().second)
        else:
            # some error
            sleep(60)  # 1 minute before try again
        
# Main entrypoint
if __name__ == '__main__':
    try:
        main_loop()
    except KeyboardInterrupt:
        print('\nExiting by user request.\n', file=sys.stderr)
        sys.exit(0)