from enum import Enum
from jackutil.microfunc import roundup, rounddown
from jackutil.microfunc import extractvalues

# --
# !! rule: ask (offer) > bid
# -- bid, ask is from the perspective of the broker/dealer
# -- ask is the offer, almost always higher than bid (the 
# -- highest price the broker will pay)
# --
def spread(bid,ask):
	if(ask > bid):
		return (ask - bid)
	raise RuntimeError("bid >= ask")

# -- ------------------------------------------------------------------------------------------
# -- ------------------------------------------------------------------------------------------
# -- ------------------------------------------------------------------------------------------
# --
# !! mid price is **very slightly aggressive** by using
# !! roundup for buy order, and rounddown for sell order
# --
def def_buy_price(bid,ask):
	return roundup(ask,2)
	
def def_sell_price(bid,ask):
	return rounddown(bid,2)
	
def mid_buy_price(bid,ask):
	return roundup((bid+ask)/2,2)
	
def mid_sell_price(bid,ask):
	return rounddown((bid+ask)/2,2)
	
def percent_premium_buy_price(bid,ask,p1):
	assert(p1 is not None), "p1 cannot be None"
	return roundup(ask*(1+p1/100),2)
	
def percent_premium_sell_price(bid,ask,p1):
	assert(p1 is not None), "p1 cannot be None"
	return rounddown(bid*(1-p1/100),2)
	
def dollar_premium_buy_price(bid,ask,p1):
	assert(p1 is not None), "p1 cannot be None"
	return roundup(ask+p1,2)
	
def dollar_premium_sell_price(bid,ask,p1):
	assert(p1 is not None), "p1 cannot be None"
	return rounddown(bid-p1,2)
	
# -- ------------------------------------------------------------------------------------------
# -- ------------------------------------------------------------------------------------------
# -- ------------------------------------------------------------------------------------------
class Side(Enum):
	BUY = 1
	SELL = 2

class EI(Enum):
	# --
	# -- default: buy at ask, sell at bid
	# --
	DEFAULT = 0
	# --
	# -- default: buy,sell at mid 
	# -- round up for buy, round down for sell after 2 decimal point
	# --
	MIDPOINT = 1
	# --
	# -- default: buy,sell at premium
	# -- round up for buy, round down for sell after 2 decimal point
	# --
	PERCENT_PREMIUM = 2
	DOLLAR_PREMIUM = 3

pricing_func_map = {
	Side.BUY: {
		EI.DEFAULT: ( def_buy_price, mid_buy_price, None ),
		EI.MIDPOINT: mid_buy_price,
		EI.PERCENT_PREMIUM: percent_premium_buy_price,
		EI.DOLLAR_PREMIUM: dollar_premium_buy_price,
	},
	Side.SELL: {
		EI.DEFAULT: ( def_sell_price, mid_sell_price, None ),
		EI.MIDPOINT: mid_sell_price,
		EI.PERCENT_PREMIUM: percent_premium_sell_price,
		EI.DOLLAR_PREMIUM: dollar_premium_sell_price,
	}
}

# --
# -- maxtps: max threshold per share
# -- mintps: min threshold per share
# --
def call_with_value(func, value_map):
	func_args_key_vec = func.__code__.co_varnames[:func.__code__.co_argcount]
	func_call_param_map = extractvalues(value_map, func_args_key_vec)
	return func(**func_call_param_map)

def compute_limit_price(*,bid=None,ask=None,action=None,ei=EI.DEFAULT,maxtps=0.05,mintps=None,p1=None):
	rt_args = locals().copy()
	if(isinstance(action,str)):
		action = Side[action]
	if(isinstance(ei,str)):
		ei= EI[ei]
	# --
	pricing_func = pricing_func_map[action][ei]
	if(pricing_func is None):
		raise RuntimeError("requested combination has no impl:"+str(rt_args))
	# --
	# -- single pricing func
	# --
	if(callable(pricing_func)):
		return call_with_value(pricing_func, rt_args)
	# --
	# -- pricing func is list
	# --
	ba_spread = spread(bid, ask)
	if(mintps is not None and ba_spread<mintps):
		pricing_func = pricing_func[2]
	elif(maxtps is not None and ba_spread>maxtps):
		pricing_func = pricing_func[1]
	else:
		pricing_func = pricing_func[0]
	if(pricing_func is None):
		raise RuntimeError("requested combination has no impl:"+str(rt_args))
	return call_with_value(pricing_func, rt_args)

