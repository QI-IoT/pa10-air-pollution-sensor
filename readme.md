# Introduction

A air pollution sensor Python script that make a UDOO Neo broad connect
with an Android device.

# Required Python Modules

The required modules are

1.  PyBluez

They can be installed with the following command:
```
$ sudo pip install -r requirements.txt
```
If you encounter errors during the installation, please refer to FAQ
section.

# Bluetooth Setup
First, you need to put your Bluetooth adapter in discoverable mode with
```
$ sudo hciconfig hci0 piscan
```
The default device name is `udoo-0`. To customize your Bluetooth device
name, please refer to FAQ section.

You can then use `bluez-simple-agent` to pair your Android device with
your UDOO board. Run the following script:
```
$ sudo bluez-simple-agent
```
You only need to pair UDOO board with your Android phone once. Once they
are paired, you can skip this step in the future. After you pair your
Android device with your UDOO board, you need to add the serial port
profile
```
$ sudo sdptool add sp
```

# Usage
Run the following command on an UDOO Neo to start RFCOMM server:
```
$ python air-pollution-sensor.py
```

# Architecture
This is a typical asynchronous network program. The program needs to
read sensor outputs, write the output values into a local database, and
then send the real time data to one or more Android clients over
Bluetooth.

If a client requests history data, the program has to do SQL query from
the local database, compile the result into CSV format and send it to
the client.

It is simple when there is only one client. We can use a infinite loop
to handle the requests. However, if there are multiple clients, querying
local database for history data might take a long period of time and
eventually blocks the request from other clients.

To address this issue, it would be better if we split the program into
multiple threads, let these threads focus on their own jobs, and talk to
each other through `get()` method, global variables, or a database.

## Main Thread
The main thread starts sensor server thread and Bluetooth server thread.
After that, it enters a infinite loop and does nothing.

## Sensor Server
The *sensor server* thread has the following features:
1. Read the sensor every *t* seconds;
2. Save the sensor output in a local variable and provide a *get()*
method;
3. Write the sensor output into a local SQLite database in which each
sensor has its own table with key being the epoch time and value being
the output value.

## Bluetooth Server and Client Handler
The *Bluetooth server* handles Bluetooth connections as well as requests
sent from the Android clients. A client handler is created by the server
where there is a new connection. They have the following features:
1. Handle Bluetooth connections.
2. Create a client handler for each client. Each client handler is also
an independent thread that sends no data, real-time data, or history
data according to the current status: `status == 0` means that server
will not send data to that client.
3. If `status == 1`, the client handler will get the real-time output
from the sensor server and send it to the client socket over Bluetooth.
4. If `status == 2`, the client handler will query the history from the
local database and send it to the client socket over Bluetooth.

## SQLite Database
All the sensor history is stored here. Since the module is thread-safe,
we don't need to create a proxy to handle database R/W.

# FAQ
* Why `pip` cannot verify server's certificates?

   This might happen if your system time is not properly synced. You may
   first check your system time with `date` command. If so, then use
   ```
   $ sudo service ntp stop
   $ sudo ntpdate -u time.nist.gov
   $ sudo service ntp start
   ```
   To sync your system time with an NTP server. If unfortunately, this
   still does not work, you will need to set your system time manually
   with
   ```
   $ sudo date MMDDhhmmyyyy[.ss]
   ```

* How to customize Bluetooth broadcast name?

   The default broadcast name of UDOO Neo board is `udoo-0`, if you want
   to customize its name, create a `machine-info` file in `/etc` folder,
   and add `PRETTY_HOSTNAME=device-name`. After that, restart your
   Bluetooth service with
   ```
   $ sudo service bluetooth restart
   ```