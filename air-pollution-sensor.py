from btserver import BTServer
from btserver import BTError
from sensor import SensorServer

import argparse
import asyncore
import json
import logging
import sqlite3
from threading import Thread
from time import gmtime, sleep, strftime, time

logger = logging.getLogger(__name__)


if __name__ == '__main__':
    # Create option parser
    usage = "usage: %prog [options] arg"
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", dest="output_format", default="csv",
                        help="set output format: csv, json")
    parser.add_argument("--database", dest="database_name", default="air_pollution_data.db",
                        help="specify database file")

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
    sensor_server = SensorServer(database_name=args.database_name)
    sensor_server.daemon = True
    sensor_server.start()

    # Create database connection and retrieve its cursor
    try:
        db_conn = sqlite3.connect(args.database_name)
        db_cur = db_conn.cursor()
    except Exception as e:
        logger.error("Error connecting the database {}, reason: {}".format(args.database_name, e.message))

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
            # Create CSV message "'real-time', time, temp, SN1, SN2, SN3, SN4, PM25".
            msg = "real-time, {}, {}, {}, {}, {}, {}, {}".format(epoch_time, temp, SN1, SN2, SN3, SN4, PM25)
        elif args.output_format == "json":
            # Create JSON message.
            output = {'type': 'real-time',
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

        for client_handler in bt_server.get_active_client_handlers():
            # Use a copy() to get the copy of the set, avoiding 'set change size during iteration' error
            if client_handler.sending_status.get('history')[0]:
                start_time = client_handler.sending_status.get('history')[1]
                end_time = client_handler.sending_status.get('history')[2]
                logger.info("Client requests history between {} and {}"
                            .format(strftime("%Y-%m-%d %H:%M:%S", gmtime(start_time)),
                                    strftime("%Y-%m-%d %H:%M:%S", gmtime(end_time))))
                print "Client requests history between {} and {}"\
                    .format(strftime("%Y-%m-%d %H:%M:%S", gmtime(start_time)),
                            strftime("%Y-%m-%d %H:%M:%S", gmtime(end_time)))
                # Reset history status
                client_handler.sending_status['history'] = [False, -1, -1]

                # Here we need to use SQL query to look up history data. We have to do it in a smart way since there
                # could be tens of thousands of data in a single table. If we JOIN two or three tables together, we
                # can easily get a huge table and could also be very slow.

            elif client_handler.sending_status.get('real-time'):
                try:
                    client_handler.send(msg)
                except Exception as e:
                    BTError.print_error(handler=client_handler, error=BTError.ERR_WRITE, error_message=repr(e))
                    client_handler.handle_close()
        # Sleep for 3 seconds
        sleep(3)
