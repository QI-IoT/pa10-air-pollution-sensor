from time import sleep

from sensor import SensorServer

if __name__ == '__main__':
    sensor_server = SensorServer()
    sensor_server.daemon = True
    sensor_server.start()

    while True:
        sensor_output = sensor_server.get_sensor_output()
        print sensor_output
        print "Wait for 1 second."
        sleep(1)
