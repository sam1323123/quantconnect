
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
