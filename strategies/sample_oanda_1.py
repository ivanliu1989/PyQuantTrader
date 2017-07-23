#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Created on Sun Jul 23 14:31:51 2017

@author: Ivan Liu
"""

from sklearn.model_selection import TimeSeriesSplit
from sklearn.utils import indexable
from sklearn.utils.validation import _num_samples
import numpy as np
import backtrader as bt
import backtrader.indicators as btind
import datetime as dt
import pandas as pd
from pandas import Series, DataFrame
import random
from copy import deepcopy

# Load PyQuantTrader custom classes
import PyQuantTrader.validation.walkforward as wfd