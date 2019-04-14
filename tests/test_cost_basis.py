import datetime
import pytz
import csv
import decimal
import collections

import cccalc.types
import cccalc.parser
import cccalc.run


class TestCostBasis(object):
    def test_fifo_step_through(self):

        cbq = cccalc.types.CostBasisQueue('FOOCOIN', 'USD', cccalc.types.BasisMethod.FIFO)
        cbq.load(open('tests/csvs/cbq-1.csv'))

        fills = list(cccalc.parser.parse(open('tests/csvs/fills-1.csv')))
        assert len(fills) == 3

        # verify state of cbq
        assert len(cbq.segments) == 2
        assert sum([segment.size for segment in cbq.segments]) == decimal.Decimal('2.0')

        ##### process tidflt1 and verify gains calculated correctly
        gains_fill_1 = cbq.process_fill(fills[0])
        assert gains_fill_1 == {
            cccalc.types.GainType.LongTerm: decimal.Decimal('28.545')
        }

        # verify state of cbq, still 2 segments but less holdings
        assert len(cbq.segments) == 2
        assert cbq.segments[0].size == decimal.Decimal('0.7')
        assert cbq.segments[1].size == decimal.Decimal('1.0')


        ##### process tidflt2 and verify that there are no gains since it's a buy but there are now 3 segments
        gains_fill_2 = cbq.process_fill(fills[1])
        assert gains_fill_2 == {}
        assert len(cbq.segments) == 3

        assert cbq.segments[2].trade_id == 'tidf1t2'
        assert sum([segment.size for segment in cbq.segments]) == decimal.Decimal('1.9')

        print ('basis queue:')
        print(cbq)
        print ('end queue')

        ##### process tidflt3 and verify gains calculated correctly
        gains_fill_3 = cbq.process_fill(fills[2])


        # verify state of cbq, now 1 segment left and it's the tidfl2 one
        # it was a SELL which is going to go through most of the remaining holdings, use up 2 CBQ segments and
        # leave a single partial CBQ segment left.
        assert len(cbq.segments) == 1
        assert sum([segment.size for segment in cbq.segments]) == decimal.Decimal('0.1')
        assert cbq.segments[0].trade_id == 'tidf1t2'
        assert cbq.segments[0].acquired_at == datetime.datetime(2017, 12, 2, 1, 30, 30, tzinfo=pytz.UTC)

        # The first 2 segments are from long enough ago to be long term, the last one is short and it's all at a loss.
        assert gains_fill_3 == {
            cccalc.types.GainType.LongTerm: decimal.Decimal('-35.7') + decimal.Decimal('-6'),
            cccalc.types.GainType.ShortTerm: decimal.Decimal('-13.13') # 0.1 units purchased at 215.30 sold at 84.00 at a loss of 131.3 per unit
        }