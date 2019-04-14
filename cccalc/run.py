#!/usr/bin/env python3

import sys
import cccalc.parser
import cccalc.types
import decimal
import argparse


def process_pnl(fills, cbq):
    """
    Process profit and loss related to trades of the product being traded in the fills given.  This only works
    if the cost_unit of cbq matches the price_unit of all the fills, and it only really makes sense for cases when

    Note: as of now this ignores fees, they aren't handled properly here

    :param fills: iterable of cccalc.types.Fill representing all fills that follow from the moment for which cbq
                  as given is valid, without skipping any fills that took place in the intervening time. Otherwise
                  the PNL calculations won't be valid
    :param cbq: cccalc.types.CostBasisQueue representing the state of holdings before the fills took place.
    :return: tuple of gains (short_term, long_term) denominated in the cost_unit of cbq
    """

    short_term_gains = decimal.Decimal('0')
    long_term_gains = decimal.Decimal('0')

    for fill in fills:
        print(fill)

        gains_for_fill = False

        if cbq:
            for gain_type, gain in cbq.process_fill(fill).items():
                gains_for_fill = True
                print('{0} {1:0.8f}'.format(gain_type.__name__, gain))
                if gain_type is cccalc.types.GainType.ShortTerm:
                    short_term_gains += gain
                elif gain_type is cccalc.types.GainType.LongTerm:
                    long_term_gains += gain
                else:
                    raise RuntimeError("unknown gain type")

        if not gains_for_fill:
            print('No gain/loss for this fill.')

    return short_term_gains, long_term_gains


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', dest='fills_filenames', nargs='+', help="GDAX fills CSV files to parse")
    parser.add_argument('--cost-basis', dest='cost_basis_filename', help="Cost basis CSV file to parse")
    parser.add_argument('--size-unit', dest='size_unit', help="Cost basis size unit")
    parser.add_argument('--cost-unit', dest='cost_unit', help="Cost basis unit")
    parser.add_argument('--basis-method', dest='basis_method', help="FIFO, LIFO, Average etc..")
    args = parser.parse_args()

    # cost basis
    cbq = None
    if args.cost_basis_filename:
        if not args.size_unit or not args.cost_unit:
            raise RuntimeError("Cannot use cost basis without specifying size unit and cost unit.")

        basis_method = cccalc.types.BasisMethod.from_string(args.basis_method)

        cbq = cccalc.parser.parse_cost_basis(open(args.cost_basis_filename), args.size_unit, args.cost_unit,
                                             basis_method)

        print(cbq)
        print()

    # load fills
    fills = list()
    if args.fills_filenames:
        for filename in args.fills_filenames:
            print(filename)
            for f in cccalc.parser.parse(open(filename)):
                fills.append(f)

    fills.sort(key=lambda o: o.timestamp)

    short_term_gains, long_term_gains = process_pnl(fills, cbq)

    print('Short term gains: {0:0.8f} {1}'.format(short_term_gains, args.cost_unit))
    print('Long term gains: {0:0.8f} {1}'.format(long_term_gains, args.cost_unit))

    print('Final cost basis queue remaining:\n' + repr(cbq))