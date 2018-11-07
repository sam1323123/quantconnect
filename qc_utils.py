from queue import Queue
import numpy as np



class SlidingWindow(object):

    def __init__(self, length, init_list=[]):
        self.q = Queue(length)
        self.total = None
        if init_list and len(init_list) <= length:
            for x in init_list:
                self.q.put(x)
                self.total = self.total + x if self.total is not None else x
        elif len(init_list) > length:
            raise ValueError("init_list to sliding window too large")

        self.length = length
    

    def isFull(self):
        return self.q.full()

    def _update_sma(self, data, evicted):
        if self.total is None:
            self.total = data
        else:
            self.total = self.total - evicted + data

    def update(self, data):
        if not self.q.full():
            self.q.put(data)
            evicted = None
        else:
            evicted = self.q.get()
            self.q.put(data)
        if evicted is not None:
            self._update_sma(data, evicted)
        return evicted


    # returns a list of all elements currently in the sliding window
    def to_list(self):
        new_q = Queue(self.length)
        ret = []
        while not self.q.empty():
            x = self.q.get()
            new_q.put(x)
            ret.append(x)

        self.q = new_q
        return ret

    # get simple moving average 
    def get_sma(self):
        return None if not self.isFull() else self.total / self.length

    # get variance
    def get_std(self):
        elems = self.to_list()
        return np.std(elems)
        



# Calculate SMA over lookback period.
class SMA(SlidingWindow):

    def __init__(self, lookback):
            super(SMA, self).__init__(lookback)
            self.lookback = lookback
            self.total = None

    # called at each iteration. Enters new data.
    def update(self, data):
            evicted = super(SMA, self).update(data)
            if evicted is None:
                self.total = data if self.total is None else self.total + data
            else: # an item was evicted 
                self.total = self.total - evicted + data
        
    def get_sma(self):
            if not self.isFull():
                return None
            else:
                # print self.total, (self.total / self.lookback)
                return self.total / self.lookback







sw = SlidingWindow(5, init_list=[1,1,1,1,1])
print sw.get_sma(), sw.get_std()