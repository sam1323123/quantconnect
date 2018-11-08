# My imports
from qc_utils import SlidingWindow
from qc_interface import QCAlgorithm, Resolution

# Std lib imports
from datetime import datetime, timedelta
from decimal import Decimal


class IronCondorAlgorithm(QCAlgorithm):

    class OptionType:
        PUT = 0
        CALL = 1

    class SignalType:
        NONE = 0
        OPEN = 1
        CLOSE = 2

    class TradePosition:
        SHORT = 0
        LONG = 1

        @classmethod
        # gets the quantity to long or short i.e qty = 1, position = Short => -1
        def GetQty(cls, qty, position):
            return qty if position == cls.LONG else -qty

    class PositionTracker:

        def __init__(self):
            self.positions = dict() # a map of contract symbol to positions held


        def UpdatePositon(self, symbol, total_added):
            """
            Update symbol with the total added
            :param symbol: Symbol of the instrument
            :param total_added: int. Can be positive or negative
            :return: new total
            """
            if not (symbol in self.positions):
                self.positions[symbol] = 0
            self.positions[symbol] += total_added
            return self.positions[symbol]

        def GetCurrPosition(self, symbol):
            return 0 if not (symbol in self.positions) else self.positions[symbol]

        # returns a [(symbol, qty)] array required to close out current position
        # empty array if isFlat
        def ToCloseOrders(self):
            ret = []
            for symbol in self.positions.keys():
                if self.positions[symbol] != 0:
                    ret.append((symbol, -self.positions[symbol]))
            return ret

        def IsFlat(self):
            """
            Returns True if no positions held
            :return: boolean
            """
            for v in self.positions.values():
                if v != 0:
                    return False
            return True

    def ConvertDailyResolution(self, data_handler):
        """
        Options can only execute at minute intervals This function converts the
        data_handler to exectue at daily intervals
        :param data_handler: Type = fn(slice)
        :return: Type = fn(slice)
        """

        class DailyExecutor(object):
            # qc_instance in the instanceof qc_algorithm
            def __init__(self, qc_instance, handler):
                self.last_date = None # last date handler was called
                self.handler = handler
                self.first_call = True # flag to check first time __call__ is called
                self.qc = qc_instance

            def __call__(self, slice):
                if self.first_call:
                    self.handler(slice)
                    self.last_date = self.qc.Time
                    self.first_call = False
                time_diff = self.qc.Time - self.last_date
                if time_diff.days >= 1:
                    # need >= 1 as may be weekend gap
                    self.handler(slice)
                    assert self.last_date is not self.qc.Time, "Time object is mutated"
                    self.last_date = self.qc.Time

        return DailyExecutor(self, data_handler)


    def IronCondor(self, trade_position, option_chain, qty=1):
        """
        Obtains the contracts to open an iron condor in direction of trade_position
        :param trade_position: Short or Long using TradePosition enum
        :param option_chain: OptionChain object
        :return: [(Option, qty)]
        """
        calls = []
        puts = []
        for o in option_chain:
            if o.Right == self.OptionType.CALL:
                calls.append(o)
            elif o.Right == self.OptionType.PUT:
                puts.append(o)

        # filter out valid expiry dates
        min_date = self.Time + self.holding_period

        def filter_fn(x):
            return x.Expiry > min_date  # expires after min_date

        calls = filter(filter_fn, calls)
        puts = filter(filter_fn, puts)
        # sort the calls and puts by (expiry, strike)
        calls = sorted(calls, key=lambda x: (x.Expiry, x.Strike))
        puts = sorted(puts, key=lambda x: (x.Expiry, x.Strike))
        if not calls or not puts:
            self.Debug("Cannot create Iron Condor. Not enough options in Chain")
            return []
        # Open the iron condor positions
        stock_price = float(calls[0].UnderlyingLastPrice)
        std = self.sliding_window.get_std()  # float
        short_call_strike = stock_price + (self.scale_std * std)
        long_call_strike = short_call_strike + self.spread_width
        # ensure does not go below 0
        short_put_strike = max(0.0, stock_price - (self.scale_std * std))
        long_put_strike = max(0.0, short_put_strike - self.spread_width)
        orders = []  # tuples of (symbol, qty)
        short_added = False
        inv_trade_position = self.TradePosition.LONG if trade_position == self.TradePosition.SHORT else\
            self.TradePosition.SHORT
        for call in calls:
            if not short_added and float(call.Strike) >= short_call_strike:
                # only happens once
                orders.append((call,
                               self.TradePosition.GetQty(qty, trade_position)))
                short_added = True
            elif short_added and float(call.Strike) >= long_call_strike:
                orders.append((call, self.TradePosition.GetQty(qty, inv_trade_position)))
                break
        short_added = False
        for put in puts:
            if not short_added and float(put.Strike) <= short_put_strike:
                # only happens once
                orders.append((put, self.TradePosition.GetQty(qty, trade_position)))
                short_added = True
            elif short_added and float(put.Strike) <= long_put_strike:
                orders.append((put, self.TradePosition.GetQty(qty, inv_trade_position)))
                break
        if len(orders) == 0:
            self.Debug("Cannot create a full iron condor")
            return []
        elif orders and len(orders) != 4:
            self.Debug("Iron Condor must have multiple of 4 contracts")
            return []
        return orders


    def OpenPosition(self, slice, curr_positions, signal):
        """
        Open a position in the portfolio
        :param slice: slice object from onData
        :param curr_positions: PositionTracker object
        :param signal: signal return value from GetSignal
        """
        # do nothing if position held or singal is not open
        if not (signal == self.SignalType.OPEN) or not curr_positions.IsFlat():
            return
        chain = None
        for o in slice.OptionChains:
            if o.Key == self.option.Symbol:
                chain = o.Value
                break
        if not chain:
            self.Debug("Option Chain should not be None in OpenPosition")
            return
        orders = self.IronCondor(self.TradePosition.SHORT, chain, qty=1)
        # make the orders and update position tracker
        self.Debug("Making Market Orders to Open {}".format(orders))
        for option, qty in orders:
            self.MarketOrder(option.Symbol, qty)
            self.position_tracker.UpdatePositon(option.Symbol, qty)
        # set the current expiry date of position held. Assumes all positions have same expiry
        if orders:
            self.curr_expiry = orders[0][0].Expiry
            self.Debug("Opened on {}, To Close on {}".format(self.Time, self.curr_expiry))
        return


    def ClosePosition(self, slice, curr_position, signal):
        """
        Close a position in the portfolio
        :param slice: slice object from onData
        :param signal: signal return value from GetSignal
        """
        # do nothing if no positions or not correct signal
        if not (signal == self.SignalType.CLOSE) or curr_position.IsFlat():
            return
        chain = None
        for o in slice.OptionChains:
            if o.Key == self.option.Symbol:
                chain = o.Value
                break
        if not chain:
            self.Debug("Option Chain should not be None in OpenPosition")
            return
        # orders = self.IronCondor(self.TradePosition.LONG, chain, qty=1)
        orders = curr_position.ToCloseOrders()
        self.Debug("Making Market Orders to Close {}".format(orders))
        # update position tracker and close current positions
        for symbol, qty in orders:
            self.MarketOrder(symbol, qty)
            self.position_tracker.UpdatePositon(symbol, qty)
        assert self.position_tracker.IsFlat(), "Should be flat after closing"
        self.curr_expiry = None
        return


    # used for setup in intialize to setup algo specific parameters
    # configure algorithm, setup positions/instruments
    # only called once in Initialize
    def InitPreWarmUp(self):
        self.curr_expiry = None
        self.position_tracker = self.PositionTracker()
        self.symbol = "SPY"
        self.option = self.AddOption(self.symbol, Resolution.Minute)
        self.option.SetFilter(-20, 20, timedelta(0), timedelta(30))
        self.equity = self.AddEquity(self.symbol, Resolution.Minute)
        self.lookback = 14 # 14 day lookback period
        self.sliding_window = SlidingWindow(self.lookback)
        self.scale_std = 1.0
        self.spread_width = 4.0
        self.holding_period = timedelta(days=14)
        self.SetWarmUp(self.lookback)
        return

    # additional setup after warm up period
    # only called once
    def InitPostWarmUp(self):
        return

    def GetSignal(self, slice):
        '''
        Function to generate the entry signal.
        OPEN signal when no positions held
        CLOSE signal when expiry date reached
        NONE in all other cases
        slice: slice object from OnData
        :return: Returns a value which is used by Position object
        '''
        signal = self.SignalType.NONE
        if self.position_tracker.IsFlat():
            self.Debug("Open signal generated")
            signal = self.SignalType.OPEN
        elif self.curr_expiry and (not self.position_tracker.IsFlat()) and\
                self.curr_expiry.date() <= self.Time.date():
            self.Debug("Close signal generated")
            signal = self.SignalType.CLOSE
        return signal

    # function to be converted by ConvertDailyResolution
    def DataHandler(self, slice):
        bar = slice[self.symbol]
        mid = Decimal(bar.Open + bar.Close) / Decimal(2.0)
        self.sliding_window.update(float(mid))
        if not self.warmed_up and not self.IsWarmingUp:
            # just finished warming up
            self.warmed_up = True
            self.InitPostWarmUp()
        if self.warmed_up and self.sliding_window.get_std():
            signal = self.GetSignal(slice)
            self.OpenPosition(slice, self.position_tracker, signal)
            self.ClosePosition(slice, self.position_tracker, signal)

    def Initialize(self):
        '''Initialise the data and resolution required, as well as the cash and start-end dates for your algorithm.
        All algorithms must initialized.'''

        # make sure  the start and end dates are tradeable dates or an exception occurs
        self.SetStartDate(2015, 10, 5)  # Set Start Date
        self.SetEndDate(2015, 12, 31)  # Set End Date
        self.SetCash(100000)  # Set Strategy Cash
        self.InitPreWarmUp()
        # used to detect transition from warming up to warmed uo
        self.warmed_up = False

        # datetime obj must be the same as the StartDate in SetStartDate
        self.OnDataHandler = self.ConvertDailyResolution(self.DataHandler)

    def OnData(self, slice):
        '''OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.

        Arguments:
            data: Slice object keyed by symbol containing the stock data
        '''
        self.OnDataHandler(slice)





ic = IronCondorAlgorithm()
ic.TestRun()