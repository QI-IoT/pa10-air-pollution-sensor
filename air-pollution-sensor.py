from time import sleep

from sensor import SensorServer

if __name__ == '__main__':
    server = SensorServer()

    server.start()

    while True:
        sensor_output = server.get_sensor_output()
        print sensor_output
        print "Wait for 1 second."
        sleep(1)
