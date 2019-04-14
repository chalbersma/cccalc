import datetime
import csv
import isodate
import decimal
import pytz
import collections


TZ = pytz.timezone('America/Chicago')

class Side(object):
    class Sell(object):
        pass

    class Buy(object):
        pass

    @classmethod
    def from_string(cls, s):
        if s == 'SELL':
            return cls.Sell
        elif s == 'BUY':
            return cls.Buy
        else:
            raise NotImplemented("All I understand is buys and sells.")


class BasisMethod(object):
    class FIFO(object):
        pass

    class LIFO(object):
        pass

    @classmethod
    def from_string(cls, s):
        if s == 'FIFO':
            return cls.FIFO
        elif s == 'LIFO':
            return cls.LIFO
        else:
            raise NotImplemented("All I understand is FIFO.")


class GainType(object):
    class LongTerm(object):
        pass

    class ShortTerm(object):
        pass


class Fill(object):
    def __init__(self, row_dict):
        """

        :param row_dict: dictionary with text data from GDAX csv export:
                           "trade id" -
                           "product" - "A-B" where A is the product being traded and B is the product or currency in
                                       units of which which the product is priced
                           "side" - SELL or BUY
                           "created at" - iso 8601 datetime of when the trade took place
                           "size" - quantity of product being traded
                           "size unit" - product being traded
                           "price" - trace price per 1 unit of product
                           "fee" - fee charged to execute the trade
                           "price/fee/total unit" - product or currency in units of which price, fee, and total are
                                                    denominated.
        """
        self.trade_id = row_dict['trade id']
        self.product = row_dict['product']
        self.side = Side.from_string(row_dict['side'])
        self.timestamp = isodate.parse_datetime(row_dict['created at']).astimezone(TZ)

        self.size = decimal.Decimal(row_dict['size'])
        self.size_unit = row_dict['size unit']

        self.price = decimal.Decimal(row_dict['price'])
        self.fee = decimal.Decimal(row_dict['fee'])
        self.price_unit = row_dict['price/fee/total unit']

    @property
    def total_exclusive_of_fees(self):
        return self.size * self.price

    @property
    def total(self):
        _total = self.total_exclusive_of_fees
        if self.side is Side.Sell:
            _total -= self.fee
        elif self.side is Side.Buy:
            _total += self.fee
        else:
            raise NotImplemented("All I understand is buys and sells.")

        return _total

    def __repr__(self):
        fmt_total = ('%0.2f %s' % (self.total, self.price_unit)).ljust(12)
        return '%s %0.8f %s for %s @ %s' % (self.side.__name__, self.size, self.size_unit, fmt_total, self.timestamp)

    @property
    def credit(self):
        """
        :return: Returns the total amount as a credit - negative sign if a debit. In the price_unit.
        """

        # To be on the safe side, don't deduct fees when figuring cap gains.. don't think that's deductible
        if self.side is Side.Sell:
            return self.total_exclusive_of_fees
        elif self.side is Side.Buy:
            return -(self.total_exclusive_of_fees)
        else:
            raise NotImplemented("All I understand is buys and sells.")


class CostBasisSegment(object):
    def __init__(self, trade_id, size, size_unit, acquired_at, cost, cost_unit):
        self.trade_id = trade_id
        self.size = size
        self.size_unit = size_unit
        self.acquired_at = acquired_at
        self.cost = cost
        self.cost_unit = cost_unit

    def __repr__(self):
        return 'trade={0} {1:0.8f} {2} acquired={3} cost={4} {5}'.format(self.trade_id, self.size, self.size_unit,
                                                                         self.acquired_at, self.cost, self.cost_unit)

    @classmethod
    def from_csv(cls, row_dict):
        """
        Creates a new CostBasisSegment from a csv row dict.

        :param row_dict: with keys
                           "trade id" - set this to the trade id for the fill that the product was acquired in, if any
                           "size" - quantity of product held at this cost basis currently.  The trade indicated by
                                    trade id may have been for a larger size if the cost basis queue / segment have been
                                    already partly consumed by processing later sell fills.
                           "size unit" - product held at this cost basis
                           "acquired at" - iso 8601 datetime of when the cost basis segment of product was acquired
                           "cost" - cost per 1 unit of product
                           "cost unit" - product or currency in units of which cost is denominated
        """

        trade_id = row_dict['trade id']
        size = decimal.Decimal(row_dict['size'])
        size_unit = row_dict['size unit']
        acquired_at = isodate.parse_datetime(row_dict['acquired at']).astimezone(TZ)
        cost = decimal.Decimal(row_dict['cost'])
        cost_unit = row_dict['cost unit']

        return cls(trade_id, size, size_unit, acquired_at, cost, cost_unit)


class CostBasisQueue(object):
    def __init__(self, size_unit, cost_unit, basis_method):
        self.size_unit = size_unit
        self.cost_unit = cost_unit
        self.basis_method = basis_method
        self.segments = []

    def __repr__(self):
        return 'CBQ size_unit={0} cost_unit={1} segments={2}\n'.format(self.size_unit, self.cost_unit,
                                                                       len(self.segments)) + '\n'.join([
            repr(cbs) for cbs in self.segments
        ])

    def load(self, fh):
        for row_dict in csv.DictReader(fh):
            cbs = CostBasisSegment.from_csv(row_dict)
            if cbs.size_unit != self.size_unit:
                raise RuntimeError("cost unit is incompatible {0} != {1}".format(cbs.size_unit, self.size_unit))
            if cbs.cost_unit != self.cost_unit:
                raise RuntimeError("cost unit is incompatible {0} != {1}".format(cbs.cost_unit, self.cost_unit))

            self.segments.append(cbs)

    def process_fill(self, fill):
        """
        Given a fill object, apply the fill to the cost basis queue and return the gain or loss, the unit the gain or
        loss is denominated in, and the gain/loss type (tuple).

        Note: as of now this ignores fees, they aren't handled properly here

        :return: tuple with 2 values:
                   dict with keys (GainType inner class) and values of gain
                   gain_unit
        """
        if fill.price_unit != self.cost_unit:
            raise RuntimeError("Cannot process price_unit conflict fill={0} cost={1}".format(fill.price_unit,
                                                                                             self.cost_unit))
        if fill.size_unit != self.size_unit:
            raise RuntimeError("Cannot process size_unit conflict fill={0} cost={1}".format(fill.size_unit,
                                                                                            self.size_unit))

        gains = collections.defaultdict(lambda: decimal.Decimal('0'))

        if fill.side is Side.Sell:
            size_remaining = fill.size
            while size_remaining > decimal.Decimal('0'):
                if not self.segments:
                    raise RuntimeError("Insufficient cost basis to process fill.")

                if self.basis_method is BasisMethod.FIFO:
                    segment = self.segments[0]
                elif self.basis_method is BasisMethod.LIFO:
                    segment = self.segments[-1]
                else:
                    raise NotImplemented("Basis method can't be handled.")

                #print('processing fill {0} with cost basis segment {1}'.format(fill, segment))

                size_this_segment = min(size_remaining, segment.size)

                if fill.timestamp > segment.acquired_at + datetime.timedelta(days=365.2422):
                    gain_type = GainType.LongTerm
                else:
                    gain_type = GainType.ShortTerm

                price_change = fill.price - segment.cost
                gains[gain_type] += price_change * size_this_segment

                size_remaining -= size_this_segment
                segment.size -= size_this_segment

                if segment.size == decimal.Decimal('0'):
                    if self.basis_method is BasisMethod.FIFO:
                        self.segments = self.segments[1:]
                    elif self.basis_method is BasisMethod.LIFO:
                        self.segments = self.segments[:-1]
                    else:
                        raise NotImplemented("Basis method can't be handled.")

                    #print('Segment consumed.')

        elif fill.side is Side.Buy:
            self.segments.append(CostBasisSegment(fill.trade_id, fill.size, fill.size_unit, fill.timestamp, fill.price,
                                                  self.cost_unit))
            #print('processed fill {0} added cost basis segment: {1}'.format(fill, self.segments[-1]))
        else:
            raise NotImplemented("All I understand is buys and sells.")

        return gains