# -*- coding: utf-8 -*-
"""
Created on Mon Jul 24 23:34:02 2017

@author: Ivan Liu
"""

import numpy as np
import pandas as pd
import backtrader as bt
import pykalman


class KalmanFilter(bt.Indicator):
    _mindatas = 2  # needs at least 2 data feeds

    lines = ('et', 'sqrt_qt',)

    params = dict(
        delta=1e-4,
        vt=1e-3,
    )

    def __init__(self):
        self.wt = self.p.delta / (1 - self.p.delta) * np.eye(2)
        self.theta = np.zeros(2)
        self.P = np.zeros((2, 2))
        self.R = None

        self.d1_prev = self.data1(-1)  # data1 yesterday's price

    def next(self):
        F = np.asarray([self.data0[0], 1.0]).reshape((1, 2))
        y = self.d1_prev[0]

        if self.R is not None:  # self.R starts as None, self.C set below
            self.R = self.C + self.wt
        else:
            self.R = np.zeros((2, 2))

        yhat = F.dot(self.theta)
        et = y - yhat


class KalmanSignals(bt.Indicator):
    _mindatas = 2  # needs at least 2 data feeds

    lines = ('long', 'short',)

    def __init__(self):
        kf = KalmanFilter(self.data0, self.data1)
        et, sqrt_qt = kf.lines.et, kf.lines.sqrt_qt

        self.lines.long = et < -1.0 * sqrt_qt
        # longexit is et > -1.0 * sqrt_qt ... the opposite of long
        self.lines.short = et > sqrt_qt
        # shortexit is et < sqrt_qt ... the opposite of short
        
        
class KalmanFilterMA(bt.indicators.MovingAverageBase):
    alias = ('KalmanMovingAverage',)
    lines = ('kma',)
    params = (
        ('initial_state_covariance', 1.0),
        ('observation_covariance', 1.0),
        ('transition_covariance', 0.05),
    )

    def __init__(self):
        self.addminperiod(self.p.period)  # when to deliver values
        self._dlast = self.data(-1)  # get previous day value

    def nextstart(self):
        self._k1 = self._dlast[0]
        self._c1 = self.p.initial_state_covariance

        self._kf = pykalman.KalmanFilter(
            transition_matrices=[1],
            observation_matrices=[1],
            observation_covariance=self.p.observation_covariance,
            transition_covariance=self.p.transition_covariance,
            initial_state_mean=self._k1,
            initial_state_covariance=self._c1,
        )

        self.next()

    def next(self):
        k1, self._c1 = self._kf.filter_update(self._k1, self._c1, self.data[0])
        self.lines.kma[0] = self._k1 = k1