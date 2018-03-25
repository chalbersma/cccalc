import isodate
import decimal
import pytz

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



class Fill(object):
    def __init__(self, row_dict):
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