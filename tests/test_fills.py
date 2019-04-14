import datetime
import pytz
import decimal

import cccalc.types
import cccalc.parser


class TestFills(object):
    def test_fill_from_csv(self):
        fills = list(cccalc.parser.parse(open('tests/csvs/fills-1.csv')))
        assert len(fills) == 3

        assert fills[0].trade_id == 'tidf1t1'
        assert fills[0].product == 'FOOCOIN-USD'
        assert fills[0].timestamp == datetime.datetime(2017, 12, 1, 21, 50, 50, tzinfo=pytz.utc)
        assert fills[0].side == cccalc.types.Side.Sell
        assert fills[0].size == decimal.Decimal('0.3')
        assert fills[0].size_unit == 'FOOCOIN'
        assert fills[0].price == decimal.Decimal('230.15')
        assert fills[0].price_unit == 'USD'

        assert fills[1].trade_id == 'tidf1t2'
        assert fills[1].product == 'FOOCOIN-USD'
        assert fills[1].timestamp == datetime.datetime(2017, 12, 2, 1, 30, 30, tzinfo=pytz.utc)
        assert fills[1].side == cccalc.types.Side.Buy
        assert fills[1].size == decimal.Decimal('0.2')
        assert fills[1].size_unit == 'FOOCOIN'
        assert fills[1].price == decimal.Decimal('215.30')
        assert fills[1].price_unit == 'USD'

        assert fills[2].trade_id == 'tidf1t3'
        assert fills[2].product == 'FOOCOIN-USD'
        assert fills[2].timestamp == datetime.datetime(2017, 12, 22, 11, 30, 29, tzinfo=pytz.utc)
        assert fills[2].side == cccalc.types.Side.Sell
        assert fills[2].size == decimal.Decimal('1.8')
        assert fills[2].size_unit == 'FOOCOIN'
        assert fills[2].price == decimal.Decimal('84.00')
        assert fills[2].price_unit == 'USD'

    def test_total_exclusive_of_fees(self):
        fills = list(cccalc.parser.parse(open('tests/csvs/fills-1.csv')))
        assert len(fills) == 3

        assert fills[0].trade_id == 'tidf1t1'
        assert fills[0].total_exclusive_of_fees == decimal.Decimal('69.045')

        assert fills[1].trade_id == 'tidf1t2'
        assert fills[1].total_exclusive_of_fees == decimal.Decimal('43.06')

        assert fills[2].trade_id == 'tidf1t3'
        assert fills[2].total_exclusive_of_fees == decimal.Decimal('151.20')