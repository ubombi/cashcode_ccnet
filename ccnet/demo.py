from ccnet import CCNET
import sys


def print_logo():
    print(chr(27) + "[2J")              # ClearScreen
    print """
    #     ___               _       ___            _       
    #    / __|  __ _   ___ | |_    / __|  ___   __| |  ___ 
    #   | (__  / _` | (_-< | ' \  | (__  / _ \ / _` | / -_)
    #    \___| \__,_| /__/ |_||_|  \___| \___/ \__,_| \___|
    #      python-ccnet lib demo  \t by CookIT             
    """


def print_balance(balance, amount=False):
    sys.stdout.write("\b\r Balance: " + str(balance))
    if amount:
        sys.stdout.write(" | Hmmm, Its " + str(amount) + ". Om nom nom nom...")
    else:
        sys.stdout.write("                                               ")
    sys.stdout.flush()


def print_device(device):
    print "\n==== Device ===="
    print(
        "PART" + str(device['Part']) + "\t"
        "SERIAL" + str(device['Serial']) + "\t"
        "ASSET(H)" + str(device['Asset']).encode('hex') + "\t"
    )
    sys.stdout.flush()


def print_bill_table(table):
    print "\n== BILL TABLE =="
    for i, bill in enumerate(table):
        if i % 4 != 0:
            sys.stdout.write("\t\t")
            sys.stdout.write(str(int(bill['amount'])) + str(bill['code']))
        else:
            sys.stdout.write("\n")
            sys.stdout.write(str(int(bill['amount'])) + str(bill['code']))


# ccnet.end()
# ccnet.retrieve()


#       ###  ####  ##   #   ###
#       #  # #     # # ##  #   #
#       #  # ####  #  # #  #   #
#       #  # #     #    #  #   #
#       ###  ####  #    #   ###

ccnet = CCNET('/dev/ttyUSB0', '03')     # Init: connect to serial
if ccnet.connect() and ccnet.start():   # reset end enable bill types
    print_logo()
    print_device(ccnet.device)
    print_bill_table(ccnet.billTable)

    balance = 0
    print "\n==== ESCROW ==== [Give me some money] \n"
    while True:
        esc = ccnet.escrow()            # Allows get cash. return {'amount', 'code'}
        if esc is not False:
            print_balance(balance, esc['amount'])
            if ccnet.stack():           # Get this bill
                balance += esc['amount']
            print_balance(balance)
else:
    print "Connection error. Check log files"
