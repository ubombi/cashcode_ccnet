import math
import struct


def return_buffer(data):
    def func():
        return data
    return func


def data_proxy(data):
    return data


def check_error(data):
    data = struct.unpack('b', data)
    if data[0] is 0:
        return "Done"
    elif data[0] is 255:
        return "Error"
    else:
        return "Unknown response"


def get_status_response(data):
    return {
        'enabledBills': data[0:3].decode('hex'),
        'highSecurity': data[3:6].decode('hex'),
    }


def enable_bill_types_request(data):
    return '34'+''.join(["%02X" % x for x in data]).strip()


def identification_response(data):
    return {
        'Part': str(data[0:15]).strip(),
        'Serial': str(data[15:27]).strip(),
        'Asset': data[27:34],
    }


def get_bill_table_response(data):
    data = bytearray(data)
    response = []
    for i in range(0, 23):
        word = data[i*5:i*5+5]
        cur_nom = word[0]
        cur_pow = word[4]
        response.append({
            'amount': cur_nom * math.pow(10, cur_pow),
            'code': str(word[1:4]),
        })
    # print response
    return response

comamnds_dict = {
    'RESET':                [return_buffer('30'), check_error],
    'GET STATUS':           [return_buffer('31'), get_status_response],
    'SET SECURITY':         [return_buffer('32'), data_proxy],
    'POLL':                 [return_buffer('33'), data_proxy],
    'ENABLE BILL TYPES':    [enable_bill_types_request, check_error],
    'STACK':                [return_buffer('35'), data_proxy],
    'RETURN':               [return_buffer('36'), data_proxy],
    'IDENTIFICATION':       [return_buffer('37'), identification_response],
    'HOLD':                 [return_buffer('38'), data_proxy],
    'SET BARCODE PARAMETERS': [return_buffer('39'), data_proxy],
    'EXTRACT BARCODE DATA': [return_buffer('3A'), data_proxy],
    'GET BILL TABLE':       [return_buffer('41'), get_bill_table_response],
    'DOWNLOAD':             [return_buffer('50'), data_proxy],
    'GET CRC32 OF THE CODE': [return_buffer('51'), data_proxy],
    'REQUEST STATISTICS':   [return_buffer('60'), data_proxy],
    'ACK':   [return_buffer('00'), data_proxy],
}


class req_res(object):
    def __init__(self, command):
        self.request = comamnds_dict[command][0]
        self.response = comamnds_dict[command][1]


class Commands(object):
    def __call__(self, command):
        return req_res(command)
