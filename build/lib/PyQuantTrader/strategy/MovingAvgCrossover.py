#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Created on Sun Jul 23 15:28:56 2017

@author: Ivan Liu
"""
import backtrader as bt 
import backtrader.indicators as btind
import datetime as dt

class SMAC(bt.Strategy):
    """A simple moving average crossover strategy; crossing of a fast and slow moving average generates buy/sell
       signals"""
    params = {"fast": 20, "slow": 50,                  # The windows for both fast and slow moving averages
              "optim": False, "optim_fs": (20, 50)}    # Used for optimization; equivalent of fast and slow, but a tuple
                                                       # The first number in the tuple is the fast MA's window, the
                                                       # second the slow MA's window
 
    def __init__(self):
        """Initialize the strategy"""
 
        self.fastma = dict()
        self.slowma = dict()
        self.regime = dict()
 
        if self.params.optim:    # Use a tuple during optimization
            self.params.fast, self.params.slow = self.params.optim_fs    # fast and slow replaced by tuple's contents
 
        if self.params.fast > self.params.slow:
            raise ValueError(
                "A SMAC strategy cannot have the fast moving average's window be " + \
                 "greater than the slow moving average window.")
 
        for d in self.getdatanames():
 
            # The moving averages
            self.fastma[d] = btind.SimpleMovingAverage(self.getdatabyname(d),      # The symbol for the moving average
                                                       period=self.params.fast,    # Fast moving average
                                                       plotname="FastMA: " + d)
            self.slowma[d] = btind.SimpleMovingAverage(self.getdatabyname(d),      # The symbol for the moving average
                                                       period=self.params.slow,    # Slow moving average
                                                       plotname="SlowMA: " + d)
 
            # Get the regime
            self.regime[d] = self.fastma[d] - self.slowma[d]    # Positive when bullish
 
    def next(self):
        """Define what will be done in a single step, including creating and closing trades"""
        for d in self.getdatanames():    # Looping through all symbols
            pos = self.getpositionbyname(d).size or 0
            if pos == 0:    # Are we out of the market?
                # Consider the possibility of entrance
                # Notice the indexing; [0] always mens the present bar, and [-1] the bar immediately preceding
                # Thus, the condition below translates to: "If today the regime is bullish (greater than
                # 0) and yesterday the regime was not bullish"
                if self.regime[d][0] > 0 and self.regime[d][-1] <= 0:    # A buy signal
                    self.buy(data=self.getdatabyname(d))
 
            else:    # We have an open position
                if self.regime[d][0] <= 0 and self.regime[d][-1] > 0:    # A sell signal
                    self.sell(data=self.getdatabyname(d))
 


class SMACWalkForward(bt.Strategy):
    """The SMAC strategy but in a walk-forward analysis context"""
    params = {"start_dates": None,    # Starting days for trading periods (a list)
              "end_dates": None,      # Ending day for trading periods (a list)
              "fast": None,           # List of fast moving average windows, corresponding to start dates (a list)
              "slow": None}           # Like fast, but for slow moving average window (a list)
    # All the above lists must be of the same length, and they all line up
 
    def __init__(self):
        """Initialize the strategy"""
 
        self.fastma = dict()
        self.slowma = dict()
        self.regime = dict()
 
        self.date_combos = [c for c in zip(self.p.start_dates, self.p.end_dates)]
 
        # Error checking
        if type(self.p.start_dates) is not list or type(self.p.end_dates) is not list or \
           type(self.p.fast) is not list or type(self.p.slow) is not list:
            raise ValueError("Must past lists filled with numbers to params start_dates, end_dates, fast, slow.")
        elif len(self.p.start_dates) != len(self.p.end_dates) or \
            len(self.p.fast) != len(self.p.start_dates) or len(self.p.slow) != len(self.p.start_dates):
            raise ValueError("All lists passed to params must have same length.")
 
        for d in self.getdatanames():
            self.fastma[d] = dict()
            self.slowma[d] = dict()
            self.regime[d] = dict()
 
            # Additional indexing, allowing for differing start/end dates
            for sd, ed, f, s in zip(self.p.start_dates, self.p.end_dates, self.p.fast, self.p.slow):
                # More error checking
                if type(f) is not int or type(s) is not int:
                    raise ValueError("Must include only integers in fast, slow.")
                elif f > s:
                    raise ValueError("Elements in fast cannot exceed elements in slow.")
                elif f <= 0 or s <= 0:
                    raise ValueError("Moving average windows must be positive.")
 
                if type(sd) is not dt.date or type(ed) is not dt.date:
                    raise ValueError("Only datetime dates allowed in start_dates, end_dates.")
                elif ed - sd < dt.timedelta(0):
                    raise ValueError("Start dates must always be before end dates.")
 
                # The moving averages
                # Notice that different moving averages are obtained for different combinations of
                # start/end dates
                self.fastma[d][(sd, ed)] = btind.SimpleMovingAverage(self.getdatabyname(d),
                                                           period=f,
                                                           plot=False)
                self.slowma[d][(sd, ed)] = btind.SimpleMovingAverage(self.getdatabyname(d),
                                                           period=s,
                                                           plot=False)
 
                # Get the regime
                self.regime[d][(sd, ed)] = self.fastma[d][(sd, ed)] - self.slowma[d][(sd, ed)]
                # In the future, use the backtrader indicator btind.CrossOver()
 
    def next(self):
        """Define what will be done in a single step, including creating and closing trades"""
 
        # Determine which set of moving averages to use
        curdate = self.datetime.date(0)
        dtidx = None    # Will be index
        # Determine which period (if any) we are in
        for sd, ed in self.date_combos:
            # Debug output
            #print('{}: {} < {}: {}, {} < {}: {}'.format(
            #    len(self), sd, curdate, (sd <= curdate), curdate, ed, (curdate <= ed)))
            if sd <= curdate and curdate <= ed:
                dtidx = (sd, ed)
        # Debug output
        #print('{}: the dtixdx is {}, and curdate is {};'.format(len(self), dtidx, curdate))
        for d in self.getdatanames():    # Looping through all symbols
            pos = self.getpositionbyname(d).size or 0
            if dtidx is None:    # Not in any window
                break            # Don't engage in trades
            if pos == 0:    # Are we out of the market?
                # Consider the possibility of entrance
                # Notice the indexing; [0] always mens the present bar, and [-1] the bar immediately preceding
                # Thus, the condition below translates to: "If today the regime is bullish (greater than
                # 0) and yesterday the regime was not bullish"
                if self.regime[d][dtidx][0] > 0 and self.regime[d][dtidx][-1] <= 0:    # A buy signal
                    self.buy(data=self.getdatabyname(d))
 
            else:    # We have an open position
                if self.regime[d][dtidx][0] <= 0 and self.regime[d][dtidx][-1] > 0:    # A sell signal
                    self.sell(data=self.getdatabyname(d))
		
