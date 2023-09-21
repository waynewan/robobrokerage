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

def non_empty_str(val):
	return val is not None and val.strip() !=""

def cast_value(val, type):
	if(type=="s"):
		return val
	if(type=="f"):
		return float(val)
	if(type=="i"):
		return int(val)
	raise Exception(f"bad type '{type}'")

# --
# -- tsv_orders: symbol, qty (1 order/line)
# -- qty: +ve=>BUY, -ve=>SELL, 0=>ignore
# --
def parse_one_order(order,header,def_values):
	symbol,qty = order[0:2]
	other_fields = order[2:]
	qty = int(qty.strip())
	order_values = { key:cast_value(value,header[key]) for key,value in zip(header.keys(),other_fields) if(non_empty_str(value)) }
	order_values.update({
		"Symbol" : symbol.strip(),
		"Action" : ["BUY","SELL"][qty<0],
		"Quantity" : abs(qty),
	})
	control_values = {
		"Status" : 'INIT',
		"Message" : '',
		"Time" : datetime.datetime.now(),
		"Order#" : '',
		"Response" : {},
		"Retry" : 0,
	}
	# --
	# -- I don't care about unused key:field
	# --
	init_order = {
		"Price" : None,
	}
	init_order.update(def_values)
	init_order.update(order_values)
	init_order.update(control_values)
	return init_order

def init_basket(tsv_orders,header=[],def_values={},field_delimit='	',order_delimit='\n',batch=None):
	orders = []
	header = { k:t for t,k in [ h.split(':') for h in header ] }
	for line in tsv_orders.split(order_delimit):
		line = line.strip()
		if(line=="" or line.startswith("#") or line.startswith("--")):
			continue
		orders.append(parse_one_order(line.split(field_delimit), header, def_values))
	new_basket = pd.DataFrame(data=orders)
	if(batch is None):
		return new_basket
	return pd.concat([batch, new_basket], axis=0).reset_index(drop=True)

def print_error(nn,order,err):
	order = order.to_dict()
	print(f"#### trade {nn}/{order['Symbol']}: ERR ####")
	pprint.pprint(order)
	traceback.print_exc()

def send_basket(broker,basket,onerror=print_error):
	retry_orders = []
	for nn,order in basket[basket['Status']=='INIT'].iterrows():
		try:
			basket.loc[nn,'Time'] = datetime.datetime.now()
			response = broker.new_order_by_qty(
				account=order['Subacct'],
				action=order['Action'],
				symbol=order['Symbol'],
				quantity=order['Quantity'],
				price=order['Price'],
				capital_limit=None,
				auto_send=True,
			)
			basket.loc[nn,'Response'] = str(response)
			basket.loc[nn,'Status'] = 'SUCCESS'
			basket.loc[nn,'Order#'] = response['Order#']
		except Exception as ex:
			retry_order = order.copy()
			retry_order['Retry'] += 1
			retry_order['Status'] = 'INIT'
			retry_order['Time'] = datetime.datetime.now()
			retry_orders.append(retry_order)
			# --
			if(onerror is not None):
				onerror(nn,order,ex)
			basket.loc[nn,'Message'] = f'{ex}'
			basket.loc[nn,'Status'] = 'FAILED'
	return pd.DataFrame(retry_orders)

