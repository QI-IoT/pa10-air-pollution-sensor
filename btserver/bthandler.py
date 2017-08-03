import asyncore
import logging
import re
from bterror import BTError

logger = logging.getLogger(__name__)


class BTClientHandler(asyncore.dispatcher_with_send):
    """BT handler for client-side socket"""

    def __init__(self, socket, server):
        asyncore.dispatcher_with_send.__init__(self, socket)
        self.server = server
        self.data = ""
        self.sending_status = {'real-time': False, 'history': [True, -1, -1]}

    def handle_read(self):
        try:
            data = self.recv(1024)
            if not data:
                return

            lf_char_index = data.find('\n')

            if lf_char_index == -1:
                # No new line character in data, so we append all.
                self.data += data
            else:
                # We see a new line character in data, so append rest and handle.
                self.data += data[:lf_char_index]
                print "Received [{}]".format(self.data)

                self.handle_command(self.data)

                # Clear the buffer
                self.data = ""
        except Exception as e:
            BTError.print_error(handler=self, error=BTError.ERR_READ, error_message=repr(e))
            self.data = ""
            self.handle_close()

    def handle_command(self, command):
        # We should support following commands:
        # - start
        #       Start sending real time data by setting 'sending_status' variable to 0
        # - stop
        #       Stop sending real time data by setting 'sending_status' variable to False
        # - history start_time end_time
        #       Stop sending real time data, and query the history data from the database. Getting history data might
        #       take some time so we should use a different thread to handle this request
        if re.match('stop', command) is not None:
            self.sending_status['real-time'] = False
            pass

        if re.match('start', command) is not None:
            self.sending_status['real-time'] = True
            pass

        result = re.match(r"history (\d+) (\d+)", command)
        if result is not None:
            self.sending_status['history'] = [True, int(result.group(1)), int(result.group(2))]

    def handle_close(self):
        # flush the buffer
        while self.writable():
            self.handle_write()

        self.server.active_client_handlers.remove(self)
        self.close()
