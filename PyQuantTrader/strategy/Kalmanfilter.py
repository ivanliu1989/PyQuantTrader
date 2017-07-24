# -*- coding: utf-8 -*-
"""
Created on Mon Jul 24 23:35:59 2017

@author: Ivan Liu
"""

import backtrader as bt 
from PyQuantTrader.indicators import KalmanSignals

class KalmanFilterStrategy(bt.Strategy):
    params = (
    )

    def __init__(self):
        self.ksig = KalmanSignals(self.data0, self.data1)

    def next(self):
        size = self.position.size
        if not size:
            if self.ksig.long:
                self.buy()
            elif self.ksig.short:
                self.sell()

        elif size > 0:
            if not self.ksig.long:
                self.close()
        elif not self.ksig.short:  # implicit size < 0
            self.close()