from jackutil.browser_mgr import *

from .crawler_util import *
from .trade_common import *

from .fidelity import fid_menu_accounts
from .fidelity import fid_menu_site
from .fidelity import fid_page_auth
from .fidelity import fid_page_auth_20230916
from .fidelity import fid_page_landing
from .fidelity import fid_page_activity_20230920
from .fidelity import fid_page_order
from .fidelity import fid_page_summary
from .fidelity import fid_page_position_v1
from .fidelity import fid_page_position_v2

from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait

import pandas as pd
import argparse
import datetime
import getpass
import hashlib
import pickle
import os
import sys
import tempfile
import time
import locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF8')

# --
# --
# --
class fidelity_webbroker:
	def __init__(self,*,login,secret,doInit=True,tmpdir=os.path.expanduser('~/trash')):
		self.driver = None
		self.persist_name = {
			'broker':'fidelity_webbroker_20230101',
			'login':login,
			'secret':secret
		}
		subdir = temporary_dir_name(self.persist_name)
		self.rootdir = f'{tmpdir}/{subdir}'
		if(doInit):
			self.init_broker_session()

	def init_broker_session(self):
		try:
			self.driver = self.reconnect_session()
		except:
			self.rootdir,self.driver = self.create_browser(self.rootdir)
			self.present_broker_login_page()
	
	def create_browser(self,rootdir=None):
		if(rootdir is None):
			rootdir=tempfile.TemporaryDirectory()
		driver = create_new_browser(rootdir=rootdir,persist_name=self.persist_name)
		driver.current_url #// test is the remote still reachable
		return (rootdir,driver)

	def reconnect_session(self):
		driver = reconnect_browser(persist_name=self.persist_name)
		driver.current_url #// test is the remote still reachable
		return driver

	#//
	#//
	#//
	def wait_page_auth(self,timeout=10):
		for nn in range(0,timeout):
			try:
				print("fid_page_auth.wait_page_loaded")
				page_loaded = fid_page_auth.wait_page_loaded(self.driver,timeout=1)
				return fid_page_auth
			except:
				pass
			try:
				print("fid_page_auth_20230916.wait_page_loaded")
				page_loaded = fid_page_auth_20230916.wait_page_loaded(self.driver,timeout=1)
				return fid_page_auth_20230916
			except:
				pass
		raise Exception("Timeout waiting for auth page load")

	def present_broker_login_page(self):
		fid_page_landing.goto_page(self.driver)
		self.driver.maximize_window()
		fid_page_landing.wait_page_loaded(self.driver,timeout=10)
		# --
		fid_page_landing.click_login_btn(self.driver)
		auth = self.wait_page_auth()
		# --
		auth.fill_password_inp(self.driver,"*************")
		auth.fill_username_inp(self.driver,self.persist_name['login'])

	def broker_logout(self):
		fid_menu_site.click_menu_label(self.driver,"LOGOUT")

	def wait_for_login_complete(self,waitsec=86400):
		# --
		# -- force post login landing page to summary
		# --
		for ii in range(0, waitsec):
			try:
				fid_page_position_v1.wait_page_loaded(self.driver,timeout=1)
				fid_page_summary.goto_page(self.driver)
			except:
				pass
			try:
				fid_page_summary.wait_page_loaded(self.driver,timeout=1)
				break
			except:
				pass

	# --
	# --
	# --
	def get_history(self,*,subacct=None,days_opt='10',include_raw=False,include_details=True):
		fid_page_activity_20230920.goto_page(self.driver)
		fid_page_activity_20230920.wait_page_loaded(self.driver)
		fid_page_activity_20230920.select_history_only(self.driver)
		fid_page_activity_20230920.wait_page_loaded(self.driver)
		# --
		fid_menu_accounts.select_account(self.driver,subacct)
		fid_menu_accounts.wait_page_loaded(self.driver)
		# --
		# !! must be done last; otherwise, get reset by other changes
		# --
		fid_page_activity_20230920.select_date_filter(self.driver,days_opt=days_opt)
		fid_page_activity_20230920.wait_page_loaded(self.driver)
		# --
		fid_page_activity_20230920.view_all_txns(self.driver)
		fid_page_activity_20230920.wait_page_loaded(self.driver)
		# --
		raw_transactions = fid_page_activity_20230920.raw_transactions(self.driver,incl_details=include_details)
		formatted_transactions = fid_page_activity_20230920.formatted_transactions(raw_transactions)
		if(include_raw):
			return (raw_transactions,formatted_transactions)
		else:
			return formatted_transactions

	# --
	# --
	# --
	def get_positions(self,*,subacct=None,include_raw=False,parse_col=True):
		fid_page_position_v2.goto_page(self.driver)
		fid_page_position_v2.wait_page_loaded(self.driver)
		# --
		fid_page_position_v2.select_overview_tab(self.driver)
		fid_page_position_v2.wait_page_loaded(self.driver)
		# --
		fid_menu_accounts.select_account(self.driver,subacct)
		fid_page_position_v2.wait_page_loaded(self.driver)
		# --
		header = fid_page_position_v2.raw_header(self.driver)
		raw_data = fid_page_position_v2.raw_data(self.driver,header=header)
		# --
		data_formatter = fid_page_position_v2
		if(not fid_page_position_v2.verify_header_version(header)):
			data_formatter = fid_page_position_v1
		# --
		expanded = data_formatter.expand_position_table(raw_data)
		if(not parse_col):
			if(include_raw):
				return (raw_data,expanded,None)
			else:
				return expanded
		else:
			formatted = data_formatter.format_position_table(expanded)
			if(include_raw):
				return (raw_data,expanded,formatted)
			else:
				# !!
				# !! this is default behavior
				# !!
				return formatted

	# --
	# --
	# --
	def new_order_by_qty(self,*,account,action,symbol,quantity,price=None,capital_limit=None,auto_send=True):
		fid_page_order.goto_page_with_symbol(self.driver,symbol)
		fid_page_order.raise_if_symbol_not_found(self.driver)
		account_selected = fid_page_order.select_account(self.driver,account)
		order_action = fid_page_order.select_action(self.driver,action)
		fid_page_order.set_quantity(self.driver,quantity)
		triggered_limit_price_rule = None
		current_market = fid_page_order.get_current_market(self.driver)
		if(price is None or np.isnan(price)):
			triggered_limit_price_rule,limit_price = compute_limit_price(action=action,qty=quantity,**current_market)
			fid_page_order.set_limit_price(self.driver,limit_price)
		else:
			fid_page_order.set_limit_price(self.driver,price)
			triggered_limit_price_rule = "Provided"
		fid_page_order.set_day_order(self.driver)
		fid_page_order.set_condition_none(self.driver)
		if(not auto_send):
			return None
		# --
		fid_page_order.preview_order(self.driver)
		ele = fid_page_order.wait_for_preview_accepted_or_error(self.driver)
		if(type(ele)!=type({}) and ele.text.startswith("Error")):
			raise Exception(ele.text)
		preview = fid_page_order.get_preview(self.driver)
		preview["Price Rule"] = triggered_limit_price_rule
		preview["Current Market"] = current_market
		# --
		if(capital_limit is None):
			preview['Order Preview'] = 'Bypassed'
		else:
			preview['Order Preview'] = 'OK'
			if(preview['Cost']>capital_limit):
				raise Exception('Failed capital limit test during preview')
		# --
		fid_page_order.send_order(self.driver)
		fid_page_order.wait_page_new_order_btn(self.driver)
		sent_order_result = fid_page_order.get_sent_order(self.driver)
		preview['Order#'] = sent_order_result['Order#']
		return preview

# -- rm -- 	# --
# -- rm -- 	# --
# -- rm -- 	# --
# -- rm -- 	def _cancel_order_with_btn(self,cancel_btn):
# -- rm -- 		cancel_btn.click()
# -- rm -- 		wait_for_cxl_confirm_popup = EC.presence_of_element_located((
# -- rm -- 			By.XPATH, 
# -- rm -- 			XPATH_CANCEL_TRADE_BTN
# -- rm -- 		))
# -- rm -- 		cxl_confirm_btn = WebDriverWait(self.driver, 3).until(wait_for_cxl_confirm_popup)
# -- rm -- 		cxl_confirm_btn.click()
# -- rm -- 
# -- rm -- 	def cancel_all_orders(self):
# -- rm -- 		goto_expanded_orders(self.driver)
# -- rm -- 		actions_map = create_ordnum_button_map(self.driver)
# -- rm -- 		for order_num in actions_map.keys():
# -- rm -- 			self.cancel_order(order_num)
# -- rm -- 		
# -- rm -- 	def cancel_order(self,order_num):
# -- rm -- 		goto_expanded_orders(self.driver)
# -- rm -- 		actions_map = create_ordnum_button_map(self.driver)
# -- rm -- 		cancel_btn = actions_map[order_num]['cancelBtn']
# -- rm -- 		self._cancel_order_with_btn(cancel_btn)
# -- rm -- 
# -- rm -- 	#//
# -- rm -- 	#//
# -- rm -- 	#//
# -- rm -- 	def get_positions(self):
# -- rm -- 		positions = fidelity_get_positions(self.driver)
# -- rm -- 		return positions
# -- rm -- 
# -- rm -- 	#//
# -- rm -- 	#//
# -- rm -- 	#//
# -- rm -- 	def get_orders(self):
# -- rm -- 		return fidelity_get_orders(self.driver)
# -- rm -- 
# -- rm -- 	def get_active_orders(self):
# -- rm -- 		all_orders = fidelity_get_orders(self.driver)
# -- rm -- 		live_orders = all_orders[ all_orders['Status']=='Open' ]
# -- rm -- 		return live_orders

