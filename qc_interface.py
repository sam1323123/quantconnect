from datetime import datetime, timedelta


class Resolution:

    Tick = 0 
    Second = 1
    Minute = 2
    Hourly = 3
    Daily = 4

class TimeSpan:

    @classmethod
    def FromDays(cls, days):
        return timedelta(days=days)


class OptionChain:

    # class holding the actual option chain data
    class OptionChainValue:

        class Stock(object):
            Price = 2000.0

            def __init__(self, symbol):
                self.symbol = symbol

        class Option(object):

            # not actually defined in actual Quant connect
            class Right:
                PUT = 0
                CALL = 1

            # right = call/put
            def __init__(self, right):
                self.right = right
                self.Strike = 0.0
                self.BidPrice = 0.0
                self.AskPrice = 0.0
                self.Expiry = datetime(year=2018, month=1, day=1)


        def __init__(self, symbol, date_range=None, price_range=None):
            """
            :param symbol: a string all CAPS of the ticker symbol
            :param date_range: (start datetime, end datetime)
            :param price_range: expreseed as change in price E.g (-20.00, 20.00)
            """
            self.Underlying = self.Stock(symbol)
            self.Key = symbol
            self.Value = []  # an array of options
            if date_range is None:
                # arbitrary date range
                date_range = (datetime(2018, 1, 1), datetime(2018, 12, 31))
            start, end = date_range
            num_days = (end - start).days
            for i in xrange(num_days):
                curr_date = start + timedelta(days=i)
                rights = [self.Option.Right.PUT, self.Option.Right.CALL]
                for right in rights:
                    if price_range is None:
                        price_range = (-20, 20)
                    ps,pe = price_range
                    price_deltas = [float(i) for i in xrange(int(ps), int(pe), 1)]
                    for price_delta in price_deltas:
                        o = self.Option(right=right)
                        o.Expiry = curr_date
                        o.Strike = self.Underlying.Price + price_delta
                        o.BidPrice = 0.0
                        o.AskPrice = 0.0
                        self.Value.append(o)

        def __iter__(self):
            for o in self.Value:
                yield o


    def __init__(self, symbol, date_range=None):
        self.Key = symbol
        self.Value = self.OptionChainValue(symbol, date_range)


class Bar:

    def __init__(self, symbol):
        self.Open = 2000.0
        self.Close = 2000.0
        self.High = 2000.0
        self.Low = 2000.0
        self.symbol = symbol
        pass

class Slice:

    def __init__(self):
        self.Bars = {}
        self.OptionChains = [] # array of OptionChain object
        self.Time = None # slice also has Time object

    def __getitem__(self, symbol):
        if symbol in self.Bars:
            return self.Bars[symbol]
        else:
            self.Bars[symbol] = Bar(symbol)
            return self.Bars[symbol]


class SecurityObject:

    def __init__(self, symbol):
        self.symbol = symbol
        self.IsLong = False
        self.Isshort = False
        self.Invested = False


class OptionSecurityObject:

    def __init__(self, symbol):
        self.symbol = symbol
        self.Symbol = symbol # Quantconnect's attr

    def SetFilter(self, min_strike, max_strike, min_exp, max_exp):
        assert type(min_strike) == int and type(max_strike) == int, "Args to SetFilter Type error"
        pass




class PortfolioClass:

    def __getitem__(self, symbol):
        return SecurityObject(symbol)


class QCAlgorithm:

    def __init__(self):
            self.Securities = []  # Array of Security objects.
            self.Portfolio = PortfolioClass()    # Array of SecurityHolding objects
            self.Transactions = None # Transactions helper
            self.Schedule = None    # Scheduling helper
            self.Notify = None      # Email, SMS helper
            self.Universe = None    # Universe helper
            self.Time = None # current time in the backtest

            # Not attrs in Quant connect
            self.cash = 0.0 # total cash in account
            self.start_date = None
            self.end_date = None
            self.IsWarmingUp = True
            self.warm_up_length = 0

    def Log(self, msg):
        print msg

    def Debug(self, msg):
        print msg

    def SetCash(self, cash):
        self.cash = cash

    def SetStartDate(self, year, month, day):
        self.start_date = datetime(year, month, day)
        self.Time = datetime(year, month, day)

    def SetEndDate(self, year, month, day):
        self.end_date = datetime(year, month, day)

    def SetWarmUp(self, num_periods):
        if num_periods <= 0:
            self.IsWarmingUp = False
        else:
            self.warm_up_length = num_periods

    def AddEquity(self, symbol, resolution):
        equity = SecurityObject(symbol)
        self.Securities.append(equity)

    def AddOption(self, symbol, resolution):
        ret = OptionSecurityObject(symbol)
        self.Securities.append(ret)
        return ret

    def SetHoldings(self, symbol, fraction, liquidateExistingHoldings=False):
        pass


    # Set up Requested Data, Cash, Time Period.
    def Initialize(self):
            pass

    # Other Event Handlers:
    def OnData(self, slice):
            raise NotImplementedError("On data not overriden")


    def OnEndOfDay(self, symbol):
            pass


    def OnEndOfAlgorithm(self):
            pass

    # ISimple test whether Intialize and OnData works. May not reach all code blocks in both
    # functions if there is branching based on Instance/Class parameters 
    def TestRun(self):
            self.Initialize()
            slice = Slice()
            # fill the slice object
            for security in self.Securities:
                if isinstance(security, OptionSecurityObject):
                    option_chain = OptionChain(security.symbol)
                    slice.OptionChains.append(option_chain)
                elif isinstance(security, SecurityObject):
                    slice.Bars[security.symbol] = Bar(security.symbol)
            for i in xrange(self.warm_up_length):
                self.OnData(slice)
            self.IsWarmingUp = False
            # post warm up
            curr_date = self.start_date
            while curr_date < self.end_date:
                self.Time = curr_date
                slice.Time = self.Time
                self.OnData(slice)
                curr_date += timedelta(days=1)
            return

