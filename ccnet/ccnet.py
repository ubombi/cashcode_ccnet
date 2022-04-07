from commands import Commands
import threading
import serial
import struct
import binascii
from functools import wraps
import errno
import os
import signal
import logging

__all__ = ['CCNET']

logging.basicConfig(
    filename='/tmp/ccnet_py.tmp', filemode='w+', level=logging.DEBUG)


class TimeoutError(Exception):
    pass


def timeout(seconds=30, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            result = False
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator


# cmd('POLL').request()
class CCNET(object):
    """CCNET protocol for cashcode serial"""
    states = {
        0x10: 'Power UP',
        0x11: 'Power Up with Bill in Validator',
        0x12: 'Power Up with Bill in Stacker',
        0x13: 'Initialize',
        0x14: 'Idling',
        0x15: 'Accepting',
        0x17: 'Stacking',
        0x18: 'Returning',
        0x19: 'Unit Disabled',
        0x1A: 'Holding',
        0x1B: 'Device Busy',
        0x1C: 'Rejecting',
        0x41: 'Drop Cassette Full',
        0x42: 'Drop Cassette out of position',
        0x43: 'Validator Jammed',
        0x44: 'Drop Cassette Jammed',
        0x45: 'Cheated',
        0x46: 'Pause',
        0x47: 'Failed',
        0x80: 'Escrow position',
        0x81: 'Bill stacked',
        0x82: 'Bill returned'}
    busy = False
    billTable = []
    sync = '02'
    state = 0x10
    device = {'Part': None, 'Serial': None, 'Asset': None}

    def __init__(self, port, deviceType="03"):
        self.cmd = Commands()
        self.deviceType = deviceType
        self.connection = serial.Serial(
            port=port, baudrate=9600, timeout=None,
            bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE)

    def connect(self, cb=False):
        self.connection.close()
        self.connection.open()
        try:
            if self.execute('RESET') == "Done":
                while self.execute('POLL')[0] is not 0x19:
                    threading.Event().wait(0.1)
                self.identification()
            else:
                raise Exception('Reset Error')
        except Exception as e:
            logging.error("Connection: " + str(e))
            return False
        return True

    def start(self,  billsEnable=(0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF)):
        self.billTable = self.execute('GET BILL TABLE')
        self.execute('ENABLE BILL TYPES', billsEnable)
        return True

    def identification(self):
        self.device = self.execute('IDENTIFICATION')
        return self.device

    def escrow(self):
        try:
            data = self.wait_state(0x80, dt=True)
            return self.billTable[data]
        except Exception as e:
            logging.error('ERR Escrow ' + str(e))
            return False

    def stack(self):
        logging.debug("Start stacking")
        ret = self.execute('STACK')
        res = self.wait_state(0x81)
        self.execute('ACK')
        return res

    def retrieve(self):
        logging.debug("Start returning")
        ret = self.execute('RETURN')
        return self.wait_state(0x82)

    def getState(self, h=False, dt=False):
        state = self.state
        try:
            resp = self.execute('POLL')
            self.execute('ACK')
            self.state = resp[0]
        except:
            pass
        if state is not self.state:
            logging.debug("New State:" + str(self.states[self.state]))
        if dt:
            return resp[1] if len(resp) > 1 else None
        elif h:
            return self.states[self.state]
        return self.state

    @timeout(30)
    def wait_state(self, state=0x14, dt=False):
        logging.debug("Wait for state:" + str(self.states[state]))
        if dt:
            while True:
                dt = self.getState(dt=True)  # Update self.state and get data
                if self.state is state:
                    return dt
                threading.Event().wait(0.1)
        else:
            while True:
                if self.getState() is state:
                    return True
                threading.Event().wait(0.1)

    def end(self, billsEnable=(0x00, 0x00, 0x00, 0x00, 0x00, 0xFF)):
        self.execute('ENABLE BILL TYPES', billsEnable)

    @timeout(10)
    def execute(self, command, data=None):
        if command is not "POLL":  # No pool debug, because Inf/0.1s loop
            logging.debug("Execute: " + str(command) + "[" + str(data) + "]")
        if (self.busy):
            return
        no_response = True if command is "ACK" else False
        if data is None:
            r = self.__send_command(
                self.cmd(command).request(), no_response=no_response)
        else:
            r = self.__send_command(
                self.cmd(command).request(data), no_response=no_response)
        return self.cmd(command).response(r)

    @timeout(30)
    def __send_command(self, command, no_response=False):
        self.busy = True
        try:
            cmmd = ''.join([
                self.sync, self.deviceType, self.getLenght(command), command])
            self.connection.write((cmmd + self.getCRC16(cmmd)).decode('hex'))
        except serial.SerialTimeoutException:
            print "timeout"
        except Exception as e:
                raise e
        if no_response:
            self.busy = False
            return
        try:
            response = self.connection.read(3)
            response += self.connection.read(
                int(str(response[2]).encode('hex'), 16) - 3)
            self.busy = False
            return self.checkResponse(response)
        except Exception as e:
            raise e

        self.busy = False
        return None

    @staticmethod
    def getCRC16(data, is_hex=True):
        if is_hex:
            data = bytearray.fromhex(data)
        else:
            data = bytearray(data)

        CRC = 0
        for byte in data:
            CRC ^= byte
            for j in range(0, 8):
                if (CRC & 0x0001):
                    CRC >>= 1
                    CRC ^= 0x8408
                else:
                    CRC >>= 1
        CRC = format(CRC, '02x')
        return CRC[2:4] + CRC[0:2]

    @staticmethod
    def getLenght(cmd):
        ret = "%X" % (len(cmd)/2 + 5)
        if len(ret) < 2:
            ret = '0' + ret
        return ret

    def checkResponse(self, rsp):
        resp = bytearray(rsp)
        if resp[0] != int(self.sync) or resp[1] != int(self.deviceType):
            raise Exception(
                "Wrong response target" +
                rsp[0].encode('hex') +
                rsp[1].encode('hex'))

        CRC = binascii.hexlify(resp[-2:])
        command = resp[0:-2]
        data = resp[3:-2]
        # if(CRC != self.getCRC16(command, False)):
        #     raise Exception("Wrong response command hash" + CRC
        #     "////" + self.getCRC16(command, False)
        #     "////" + binascii.hexlify(command))
        return data
