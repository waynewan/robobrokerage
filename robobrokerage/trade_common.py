def compute_limit_price(*, action, qty, bid_price, ask_price, spread_dollar_threshold=0.02, spread_percent_threshold=0.5):
	spread = ask_price - bid_price
	action = action.upper()
	if spread < 0:
		raise ValueError(f"bid_price[{bid_price}] > ask_price[{ask_price}]")
	# --
	# -- rule 1: spread <= spread_$_limit ==> buy@ask_price, sell@bid_price
	# --
	if spread <= spread_dollar_threshold:
		return "R1", ask_price if action == "BUY" else bid_price
	# --
	# -- rule 2: 2*(ask-bid)/(ask+bid) <= spread_%_limit ==> buy,sell@mid
	# --
	spread_percent_threshold = spread_percent_threshold / 100
	mid = (ask_price + bid_price) / 2.0
	if spread / mid <= spread_percent_threshold:
		rounded_mid = round(mid, 2)
		offset_table = (
			{"BUY": 0.01, "SELL":  0.00},  # rounded down
			{"BUY": 0.00, "SELL": -0.01},  # rounded up
		)[rounded_mid >= mid]
		return "R2", mid + offset_table[action]
	# --
	# -- default: buy@bid, sell@ask (place order, let user adjust limit price)
	# --
	return "RDef", bid_price if action == "BUY" else ask_price
