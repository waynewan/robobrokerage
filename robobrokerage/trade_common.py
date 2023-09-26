import pandas as pd
import numpy as np
import datetime
import pprint
import sys
import traceback

def compute_limit_price(*,action,qty,bid_price,ask_price,spread_dollar_threshold=0.02,spread_percent_threshold=0.5):
	spread = ask_price - bid_price
	action = action.upper()
	if(spread<0):
		raise Error(f"bid_price[{bid_price}] < ask_price[{ask_price}]")
	# --
	# -- rule 1: spread<=spread_$_limit ==> buy@ask_price, sell@bid_price
	# --
	if(spread<=spread_dollar_threshold):
		if(action=="BUY"):
			return "R1",ask_price
		else:
			return "R1",bid_price
	# --
	# -- rule 2: 2*(ask_price-bid_price)/(ask_price+bid_price)<=spread_%_limit ==> buy,sell@mid
	# --
	spread_percent_threshold = spread_percent_threshold / 100
	mid = (ask_price+bid_price)/2.00
	if(spread/mid<=spread_percent_threshold):
		rounded_mid = round(mid,2)
		offset_table = (
			{ "BUY": 0.01, "SELL":  0.00 }, # rounded down offset
			{ "BUY": 0.00, "SELL": -0.01 }, # rounded up offset
		)[rounded_mid>=mid]
		return "R2",mid+offset_table[action]
	# --
	# -- default rule: buy@bid_price, sell@ask_price (place order, let user adjust limit price)
	# --
	if(action=="BUY"):
		return "RDef",bid_price
	else:
		return "RDef",ask_price

