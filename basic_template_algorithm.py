from qc_utils import SMA
from qc_interface import QCAlgorithm, Resolution
import os

### <summary>
### Basic template algorithm simply initializes the date range and cash. This is a skeleton
### framework you can use for designing an algorithm.
### </summary>
class BasicTemplateAlgorithm(QCAlgorithm):
    '''Basic template algorithm simply initializes the date range and cash'''

    def Initialize(self):
        '''Initialise the data and resolution required, as well as the cash and start-end dates for your algorithm. All algorithms must initialized.'''

        self.SetStartDate(2012,1, 1)  #Set Start Date
        self.SetEndDate(2013,12,31)    #Set End Date
        self.SetCash(100000)           #Set Strategy Cash
        # Find more symbols here: http://quantconnect.com/data
        self.AddEquity("SPY", Resolution.Daily)
        # self.Debug("numpy test >>> print numpy.pi: " + str(np.pi))
        lookback = 200 # in days
        self.sma = SMA(lookback)
        self.SetWarmUp(lookback)
        
    def OnData(self, data):
        '''OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.

        Arguments:
            data: Slice object keyed by symbol containing the stock data
        '''
        bar = data['SPY']
        mid_bar = (bar.Open + bar.Close) / Decimal(2.0)
        self.sma.update(float(mid_bar))
        if not self.IsWarmingUp and self.sma.get_sma():
            ave = self.sma.get_sma()
            self.Log("Open {}, Ave {}".format(float(bar.Open), ave))
            if bar.Open > ave: 
                if not self.Portfolio['SPY'].IsLong:
                    self.SetHoldings("SPY", 1.0, liquidateExistingHoldings=True)
            elif bar.Open < ave:
                if not self.Portfolio['SPY'].IsShort:
                    self.SetHoldings('SPY', -1.0, liquidateExistingHoldings=True)




b = BasicTemplateAlgorithm()
b.TestRun()