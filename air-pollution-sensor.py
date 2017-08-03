from btserver import BTServer
from btserver import BTError
from sensor import SensorServer

import argparse
import asyncore
import json
from threading import Thread
from time import sleep, time

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
    bt_server = Thread(target=asyncore.loop, name="BT Server Thread")
    bt_server.daemon = True
    bt_server.start()

    # Create sensor server thread and run it
    sensor_server = SensorServer(database_name="air_pollution_data.db")
    sensor_server.daemon = True
    sensor_server.start()

    while True:
        msg = ""
        sensor_output = sensor_server.get_sensor_output()
        epoch_time = int(time())                    # epoch time
        temp = sensor_output.get('Temp', -1)
        SN1 = sensor_output.get('SN1', -1)
        SN2 = sensor_output.get('SN2', -1)
        SN3 = sensor_output.get('SN3', -1)
        SN4 = sensor_output.get('SN4', -1)
        PM25 = sensor_output.get('PM25', -1)

        if args.output_format == "csv":
            # Create CSV message "'realtime', time, temp, SN1, SN2, SN3, SN4, PM25".
            msg = "realtime, {}, {}, {}, {}, {}, {}, {}".format(epoch_time, temp, SN1, SN2, SN3, SN4, PM25)
        elif args.output_format == "json":
            # Create JSON message.
            output = {'type': 'realtime',
                      'time': epoch_time,
                      'temp': temp,
                      'SN1': SN1,
                      'SN2': SN2,
                      'SN3': SN3,
                      'SN4': SN4,
                      'PM25': PM25}
            msg = json.dumps(output)

        # Attach a new line character at the end of the message
        msg += '\n'

        for client_handler in bt_server.active_client_handlers.copy():
            # Use a copy() to get the copy of the set, avoiding 'set change size during iteration' error
            if client_handler.sending_status == 1:
                try:
                    client_handler.send(msg)
                except Exception as e:
                    BTError.print_error(handler=client_handler, error=BTError.ERR_WRITE, error_message=repr(e))
                    client_handler.handle_close()

            # Sleep for 3 seconds
        sleep(3)
