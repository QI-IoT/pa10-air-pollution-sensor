from btserver import BTServer
from sensor import SensorServer

import argparse
import asyncore
from threading import Thread
from time import sleep

if __name__ == '__main__':
    # Create option parser
    usage = "usage: %prog [options] arg"
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", dest="output_format", default="csv", help="set output format: csv, json")

    args = parser.parse_args()

    # Create a BT server
    uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"
    bt_service_name = "Air Pollution Sensor"
    bt_server = BTServer(uuid, bt_service_name)

    # Create BT server thread and run it
    bt_server_thread = Thread(target=asyncore.loop, name="BT Server Thread")
    bt_server_thread.daemon = True
    bt_server_thread.start()

    # Create sensor server thread and run it
    sensor_server_thread = SensorServer(database_name="air_pollution_data.db")
    sensor_server_thread.daemon = True
    sensor_server_thread.start()

    while True:
        sensor_output = sensor_server_thread.get_sensor_output()
        print sensor_output
        print "Wait for 1 second."
        sleep(1)
