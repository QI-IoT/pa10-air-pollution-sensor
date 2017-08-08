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
    parser.add_argument("--output", dest="output_format", default="json",
                        help="set output format: csv, json")
    parser.add_argument("--database", dest="database_name", default="air_pollution_data.db",
                        help="specify database file")
    parser.add_argument("--baud-rate", dest="baud_rate", default=115200,
                        help="specify Bluetooth baud rate in bps")

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

        r_msg = ""
        if args.output_format == "csv":
            # Create CSV message "'real-time', time, temp, SN1, SN2, SN3, SN4, PM25".
            r_msg = "{},{},{},{},{},{},{}".format(epoch_time, temp, SN1, SN2, SN3, SN4, PM25)
        elif args.output_format == "json":
            # Create JSON message.
            output = {'time': epoch_time,
                      'temp': temp,
                      'SN1': SN1,
                      'SN2': SN2,
                      'SN3': SN3,
                      'SN4': SN4,
                      'PM25': PM25}
            r_msg = json.dumps(output)

        for client_handler in bt_server.get_active_client_handlers():
            # Use a copy() to get the copy of the set, avoiding 'set change size during iteration' error.
            if client_handler.sending_status.get('history')[0]:
                start_time = client_handler.sending_status.get('history')[1]
                end_time = client_handler.sending_status.get('history')[2]
                fmt_start_time = strftime("%Y-%m-%d %H:%M:%S", gmtime(start_time))
                fmt_end_time = strftime("%Y-%m-%d %H:%M:%S", gmtime(end_time))

                logger.info("Client requests history between {} and {}".format(fmt_start_time, fmt_end_time))
                print "INFO: Client requests history between {} and {}".format(fmt_start_time, fmt_end_time)

                if start_time > end_time:
                    # If start time is greater than end time, ignore the command.
                    logger.warn("Start time {} is greater than end time {}, skipping..."
                                .format(fmt_start_time, fmt_end_time))
                    print "WARN: Start time {} is greater than end time {}, skipping..."\
                        .format(fmt_start_time, fmt_end_time)
                elif db_cur is None:
                    logger.error("SQL database {} is not available, skipping...".format(args.database_name))
                    print "ERROR: SQL database {} is not available, skipping...".format(args.database_name)
                else:
                    # If start time is smaller than or equal to end time AND SQL database is available, do SQL query
                    # from the database.
                    db_cur.execute("SELECT * FROM history WHERE time >= {} AND time <= {}".format(start_time, end_time))
                    # Get the result
                    results = db_cur.fetchall()
                    n = len(results)

                    logger.info("Number of data points in the results is {}, sending them at {} bps"
                                .format(n, args.baud_rate))
                    print "INFO: Number of data points in the results is {}, sending them at {} bps"\
                        .format(n, args.baud_rate)

                    i = 0
                    for row in results:
                        i += 1
                        h_msg = "{},{},{},{},{},{},{}".format(row[0], row[1], row[2], row[3], row[4], row[5], row[6])
                        client_handler.send('h' + h_msg + '\n')

                        print "INFO: Sending results ({}/{})...\r".format(i, n),
                        # A character is 8-bit long, so the whole string has (len(h_msg) + 2) * 8 bits; the default
                        # baud rate for HC-05 standard is 9600, so the time for the Bluetooth socket to process the
                        # string is (len(h_msg) + 2) * 8 / args.baud_rate; we add 10% margin to this time and wait for
                        # such a long time before we send the next row.
                        sleep(((len(h_msg) + 2) * 8 * 1.1 / args.baud_rate))

                    # Send end-of-message indicator
                    print "\nINFO: Done"
                    client_handler.send("h\n")

                # Reset history status
                client_handler.sending_status['history'] = [False, -1, -1]
            elif client_handler.sending_status.get('real-time'):
                try:
                    # Add the leading character 'r' to indicate its a real-time data, and a newline character '\n'
                    # to indicate the end of the line
                    client_handler.send('r' + r_msg + '\n')
                except Exception as e:
                    BTError.print_error(handler=client_handler, error=BTError.ERR_WRITE, error_message=repr(e))
                    client_handler.handle_close()
        # Sleep for 3 seconds
        sleep(3)
