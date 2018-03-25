#!/usr/bin/env python3

import sys
import cccalc.parser
import decimal

if __name__ == '__main__':
    #parser = argparse.ArgumentParser()
    #parser.add_argument('-f', dest='filename', help="GDAX fills file to parse")
    #args = parser.parse_args()

    credit = decimal.Decimal('0')
    total_size = decimal.Decimal('0')

    fills = list()

    for filename in sys.argv[1:]:
        for f in cccalc.parser.parse(open(filename)):
            fills.append(f)

    fills.sort(key=lambda o: o.timestamp)

    # TODO what does this code even do if there are buys?
    # need to impl FIFO and some other kinds of metrics


    for fill in fills:
        print(fill)
        credit += fill.credit
        total_size += fill.size

    print('Total credit: %0.8f' % credit)
    print('Total size (mixed products possible (warning!!!)): %0.8f' % total_size)