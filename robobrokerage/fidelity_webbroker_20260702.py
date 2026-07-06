import pandas as pd
import numpy as np
import os
import time
import locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF8')

from jackutil import browser_mgr
from . import trade_common
from .fidelity import fid_menu_accounts
from .fidelity import fid_menu_site
from .fidelity import fid_page_activity
from .fidelity import fid_page_activity_20260702
from .fidelity import fid_page_auth
from .fidelity import fid_page_landing
from .fidelity import fid_page_order
from .fidelity import fid_page_position
from .fidelity import fid_page_summary
from .fidelity.crawler_util import resolve

def goto_and_resolve(driver, *candidates):
	candidates[0].goto_page(driver)
	return resolve(driver, *candidates)


# --
# -- single point of change when Fidelity rolls a new UI version:
# -- add the new module to the front of the relevant list
# --
# !! **NEW** page class should be on top, it less likely to be obsolele !!
# --
_candidates = {
	'activity': [
		fid_page_activity_20260702,
		fid_page_activity,
	],
	'position': [fid_page_position],
	'order':    [fid_page_order],
	'summary':  [fid_page_summary],
}


class fidelity_webbroker:
	def __init__(self, *, login, secret, dbgport, browser, browserPath, driverPath, tmpdir=os.path.expanduser('~/trash')):
		self.driver = None
		self.proc = None
		# --
		if browser is None:
			raise ValueError("browser cannot be None")
		if browser not in ['chrome', 'edge']:
			raise ValueError("browser can only be 'chrome' or 'edge'")
		if browserPath is None:
			raise ValueError("browserPath cannot be None")
		if driverPath is None:
			raise ValueError("driverPath cannot be None")
		if dbgport is None:
			raise ValueError("dbgport cannot be None")
		# --
		self.browser = browser
		self.browserPath = browserPath
		self.driverPath = driverPath
		self.dbgport = dbgport
		# --
		print("browser:", self.browser)
		print("browserPath:", self.browserPath)
		print("driverPath:", self.driverPath)
		print("dbgport:", self.dbgport)
		# --
		self.persist_name = {
			'broker': 'fidelity_webbroker',
			'login': login,
			'secret': secret
		}
		subdir = browser_mgr.temporary_dir_name(self.persist_name)
		self.rootdir = f'{tmpdir}/{subdir}'
		self.init_broker_session()

	def init_broker_session(self):
		self.create_browser()

	def create_browser(self):
		self.proc = browser_mgr.start_browser_for_debug(
			port=self.dbgport,
			user_data_dir=self.rootdir,
			browser_type=self.browser,
			browserPath=self.browserPath
		)

	def connect_driver(self):
		if self.driver is None or not self.is_connected_driver():
			self.driver = browser_mgr.connect_to_browser(
				port=self.dbgport,
				browser_type=self.browser,
				driverPath=self.driverPath
			)
		print("****** driver connected ******")

	def is_connected_driver(self):
		if self.driver is None:
			return False
		return browser_mgr.is_driver_connected(self.driver)

	def disconnect_driver(self):
		self.driver.quit()
		self.driver = None
		print("****** driver disconnected ******")

	# --
	# -- navigation helpers — each resolves the active UI version after page load
	# --
	def goto_activity(self):
		return goto_and_resolve(self.driver, *_candidates['activity'])

	def goto_position(self):
		return goto_and_resolve(self.driver, *_candidates['position'])

	def goto_summary(self):
		return goto_and_resolve(self.driver, *_candidates['summary'])

	def goto_order(self, symbol):
		_candidates['order'][0].goto_page_with_symbol(self.driver, symbol)
		_candidates['order'][0].raise_if_symbol_not_found(self.driver)
		return resolve(self.driver, *_candidates['order'])

	# --
	def wait_page_auth(self, timeout=10):
		for nn in range(0, timeout):
			try:
				fid_page_auth.wait_page_loaded(self.driver, timeout=1)
				return fid_page_auth
			except:
				pass
		raise Exception("Timeout waiting for auth page load")

	def present_broker_login_page(self):
		# Note: Fidelity detects and blocks fully automated login sessions.
		# This method navigates to the login page and pre-fills the username.
		# The user must enter the password and complete any 2FA manually.
		fid_page_auth.goto_page(self.driver)
		auth = self.wait_page_auth()
		auth.fill_username_inp(self.driver, self.persist_name['login'])

	def broker_logout(self):
		fid_menu_site.click_menu_label(self.driver, "LOGOUT")

	def wait_for_login_complete(self, waitsec=86400):
		# Waits up to waitsec seconds for the summary page to appear post-login.
		# If the positions page loads first (can happen), redirects to summary.
		for ii in range(0, waitsec):
			try:
				fid_page_position.wait_page_loaded(self.driver, timeout=1)
				fid_page_summary.goto_page(self.driver)
			except:
				pass
			try:
				fid_page_summary.wait_page_loaded(self.driver, timeout=1)
				break
			except:
				pass

	# --
	def show_order_manage_page(self, *, subacct):
		m_act = self.goto_activity()
		m_act.select_orders_only(self.driver)
		m_act.wait_page_loaded(self.driver)
		fid_menu_accounts.select_account(self.driver, subacct)
		fid_menu_accounts.wait_page_loaded(self.driver)

	# --
	def get_history(self, *, subacct, days_opt='10', include_raw=False, include_details=True, getlimit=9999):
		m_act = self.goto_activity()
		m_act.select_history_only(self.driver)
		# --
		# !! possible race condition on page and panel loading !!
		# !! wait for account menu before switching account    !!
		# --
		m_act.wait_page_loaded(self.driver)
		fid_menu_accounts.wait_page_loaded(self.driver)
		fid_menu_accounts.select_account(self.driver, subacct)
		fid_menu_accounts.wait_page_loaded(self.driver)
		# --
		# !! date filter must be set last; other changes can reset it !!
		# --
		m_act.select_date_filter(self.driver, days_opt=days_opt)
		m_act.wait_page_loaded(self.driver)
		raw_transactions = m_act.raw_transactions(self.driver, incl_details=include_details,getlimit=getlimit)
		formatted = m_act.formatted_transactions(raw_transactions)
		if include_raw:
			return (raw_transactions, formatted)
		return formatted

	# --
	def get_positions(self, *, subacct, include_raw=False, parse_col=True, activate_hack=False):
		if activate_hack:
			# Resize window wide enough to expose all columns.
			# (zoom doesn't work for this purpose.)
			self.driver.set_window_size(2400, 2560)
			self.driver.set_window_position(0, 0)
		m_pos = self.goto_position()
		fid_menu_accounts.select_account(self.driver, subacct)
		m_pos.wait_page_loaded(self.driver)
		m_pos.select_overview_tab(self.driver)
		m_pos.wait_page_loaded(self.driver)
		time.sleep(2)
		if activate_hack:
			self.driver.set_window_size(1440, 2560)
			self.driver.set_window_position(0, 0)
			self.driver.maximize_window()
		# --
		header = m_pos.raw_header(self.driver)
		raw_data = m_pos.raw_data(self.driver, header=header)
		expanded = m_pos.expand_position_table(raw_data)
		if not parse_col:
			if include_raw:
				return (raw_data, expanded, None)
			return expanded
		formatted = m_pos.format_position_table(expanded)
		if include_raw:
			return (raw_data, expanded, formatted)
		return formatted

	# --
	def new_order_by_qty(self, *, account, action, symbol, quantity, price=None, capital_limit=None, auto_send=True):
		if quantity <= 0:
			raise ValueError(f"bad quantity: {quantity}")
		# --
		m_ord = self.goto_order(symbol)
		m_ord.select_account(self.driver, account)
		m_ord.select_action(self.driver, action)
		m_ord.set_quantity(self.driver, quantity)
		current_market = m_ord.get_current_market(self.driver)
		if price is None or np.isnan(price):
			triggered_limit_price_rule, limit_price = trade_common.compute_limit_price(
				action=action, qty=quantity, **current_market
			)
			m_ord.set_limit_price(self.driver, limit_price)
		else:
			m_ord.set_limit_price(self.driver, price)
			triggered_limit_price_rule = "Provided"
		m_ord.set_day_order(self.driver)
		m_ord.set_condition_none(self.driver)
		if not auto_send:
			return None
		# --
		m_ord.preview_order(self.driver)
		ele = m_ord.wait_for_preview_accepted_or_error(self.driver)
		if type(ele) != type({}) and ele.text.startswith("Error"):
			raise Exception(ele.text)
		preview = m_ord.get_preview(self.driver)
		preview["Price Rule"] = triggered_limit_price_rule
		preview["Current Market"] = current_market
		# --
		if capital_limit is None:
			preview['Order Preview'] = 'Bypassed'
		else:
			preview['Order Preview'] = 'OK'
			if preview['Cost'] > capital_limit:
				raise Exception('Failed capital limit test during preview')
		# --
		m_ord.send_order(self.driver)
		m_ord.wait_page_new_order_btn(self.driver)
		sent_order_result = m_ord.get_sent_order(self.driver)
		preview['Order#'] = sent_order_result['Order#']
		return preview
