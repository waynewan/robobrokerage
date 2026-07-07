from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.by import By

from .crawler_util import *
from jackutil.microfunc import retry
from jackutil.microfunc import str_to_dt, today, days_away

import pandas as pd
import re
import time
from tqdm.auto import tqdm
import locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF8')

# --
URL_PAGE = "https://digital.fidelity.com/ftgw/digital/portfolio/activity"
XP_DATE_SELECTOR_DD = "//filter-by-time//button"
XP_DATE_SELECTOR_OPT = '//filter-by-time/section//fds-radio-group//fds-radio'
XP_DATE_SELECTOR_APPLY = "//filter-by-time/section//*[normalize-space(text())='Apply']"
XP_LEGACY_PAGE_BTN = "//a[text()='legacy portfolio activity page']"
XP_FILTER_OPTIONS = "//filter-by-type//fds-chip"
XP_BTN = '//button'
XP_ACTIVITY_ROW = '//history-table/activity-table//div[@role="grid"]/div[@data-ref="eBody"]//div[@role="row"]'
XP_ACTIVITY_DETAIL_ROW = '//history-table/activity-table//div[@role="grid"]/div[@data-ref="eBody"]//detail-cell'
XP_INPUT_FROM_DATE = "//input[@label='From Date']"
XP_INPUT__TO__DATE = "//input[@label='To Date']"
PAGE_STATUS_UNKNOWN = "__PAGE_STATUS_UNKNOWN__"
PAGE_STATUS_OK = "__PAGE_STATUS_OK__"
XP_FILTER_OPT_CHECKED = "fds-checked"
XP_ACT_EXEC_COLLAPSED = ".//fds-button[@fds-icon-left='collapsed']"
XP_ACT_EXEC_EXPANDED = ".//fds-button[@fds-icon-left='expanded']"


def match(driver):
	return len(driver.find_elements(By.XPATH, XP_DATE_SELECTOR_DD)) > 0


def goto_page(driver):
	goto_url(driver, URL_PAGE, force=True)


def wait_page_loaded(driver, timeout=300):
	return wait_for_clickable_xpath(driver, XP_DATE_SELECTOR_DD, timeout=timeout)


def page_status(driver):
	cur_tab_ele = driver.find_elements(By.XPATH, XP_DATE_SELECTOR_DD)
	if len(cur_tab_ele) > 0:
		return PAGE_STATUS_OK
	return PAGE_STATUS_UNKNOWN


# --
# -- actions
# --
def select_date_filter_custom(driver, fromdate, todate):
	# fromdate, todate: mm/dd/yyyy
	inp_from_date = driver.find_element(By.XPATH, XP_INPUT_FROM_DATE)
	inp_from_date.clear()
	inp_from_date.send_keys(fromdate)
	inp__to__date = driver.find_element(By.XPATH, XP_INPUT__TO__DATE)
	inp__to__date.clear()
	inp__to__date.send_keys(todate)


def select_date_filter(driver, days_opt):
	def ftr():
		return __impl_select_date_filter(driver, days_opt)
	return retry(ftr, retry=10, exceptTypes=(StaleElementReferenceException,), rtnEx=False, silent=False)


def __impl_select_date_filter(driver, days_opt):
	fromdate, todate = (None, None)
	if days_opt.startswith("Custom"):
		days_opt, fromdate, todate = days_opt.split(",")
	# --
	# -- click date filter to show options
	# --
	date_filter_dd = wait_for_clickable_xpath(driver, XP_DATE_SELECTOR_DD, timeout=10)
	date_filter_dd.click()
	# --
	# -- select the option matching the partial text
	# --
	options = date_filter_dd.find_elements(By.XPATH, XP_DATE_SELECTOR_OPT)
	for option in options:
		option_text = option.text
		if days_opt.upper() in option_text.upper():
			option.click()
			if days_opt == "Custom":
				select_date_filter_custom(driver, fromdate, todate)
			apply_btn = driver.find_element(By.XPATH, XP_DATE_SELECTOR_APPLY)
			apply_btn.click()
			return option_text
	# --
	# -- nothing matched — close the dropdown
	# --
	driver.find_element(By.XPATH, XP_DATE_SELECTOR_DD).click()
	return False


def goto_legacy(driver):
	try:
		legacy_btn = driver.find_element(By.XPATH, XP_LEGACY_PAGE_BTN)
		legacy_btn.click()
		return True
	except:
		return False


# --
# -- utility
# --
def __ut_switch_option_to(ele, new_state):
	pressed_state = ele.get_attribute(XP_FILTER_OPT_CHECKED)
	if pressed_state is None:
		return None
	pressed = pressed_state.upper() == "TRUE"
	want_on = new_state.upper() == "ON"
	if want_on != pressed:
		ele.click()
		return True
	return False


def ut_switch_option_to(ele, new_state):
	for ii in range(0, 15):
		pressed = __ut_switch_option_to(ele, new_state)
		if not pressed:
			break
		time.sleep(1.0)
	return ele.get_attribute(XP_FILTER_OPT_CHECKED)


def ut_is_stale(ele):
	try:
		return ele.text
	except (StaleElementReferenceException, NoSuchElementException):
		return None


txn_type_map = {
	'DIVIDEND': 'DIV',
	'FOREIGN TAX': 'F_TAX',
	'FEE CHARGED': 'FEE',
}


def txn_category(desc):
	if desc.find('DIVIDEND') >= 0:
		if desc.find('XX)') >= 0:
			return "INTEREST"
		return txn_type_map["DIVIDEND"]
	if desc.find('FEE CHARGED') >= 0:
		return txn_type_map["FEE CHARGED"]
	if desc.find('FOREIGN TAX') >= 0:
		return txn_type_map["FOREIGN TAX"]
	if desc.find('TRANSFER') >= 0:
		return "TRANSFER"
	if desc.find('REINVEST') >= 0:
		return "SWEEP"
	if desc.find('BOUGHT') >= 0:
		return "BUY"
	if desc.find('SOLD') >= 0:
		return "SELL"
	if desc.find('ASSIGNED') >= 0:
		return "ASSIGNMENT"
	if desc.find('EXPIRED') >= 0:
		return "EXPIRED"
	if desc.find('INTEREST') >= 0:
		return "INTEREST"
	if desc.find('REDEMPTION') >= 0:
		return "REDEMPTION"
	return 'UNK'


def txn_symbol(desc):
	symbol_capturer = re.compile(r".* +(.*) +\(Cash\)")
	matches = symbol_capturer.match(desc)
	if matches is None:
		return f'NO_MATCH_ERR:{desc}'
	symbol = matches[1]
	symbol = symbol.replace('(', '').replace(')', '')
	return symbol


def select_button_only(driver, button="xxx"):
	eles = driver.find_elements(By.XPATH, XP_FILTER_OPTIONS)
	for ele in eles:
		ele_txt = ut_is_stale(ele)
		if ele_txt is None:
			continue
		if ele_txt.find(button) >= 0:
			ut_switch_option_to(ele, "on")
		else:
			ut_switch_option_to(ele, "off")


def select_history_only(driver):
	def ftr():
		# !! click twice — occasionally the first click doesn't stick !!
		select_button_only(driver, button="History")
		return select_button_only(driver, button="History")
	return retry(ftr, retry=10, exceptTypes=(StaleElementReferenceException,), rtnEx=False, silent=True)


def select_orders_only(driver):
	def ftr():
		# !! click twice — occasionally the first click doesn't stick !!
		select_button_only(driver, button="Orders")
		return select_button_only(driver, button="Orders")
	return retry(ftr, retry=10, exceptTypes=(StaleElementReferenceException,), rtnEx=False, silent=True)


def view_all_txns(driver):
	err_msg = "No 'Load more results' button"
	def ftr():
		result = click(driver, XP_BTN, "Load more results")
		if result is None:
			raise ValueError(err_msg)
	_, errors = retry(ftr, retry=10, exceptTypes=(ValueError, StaleElementReferenceException), rtnEx=True, silent=True)
	err = errors[-1]
	if err is None:
		return
	if type(err) == type(ValueError()) and str(err) == err_msg:
		return
	raise err

def expand_all_transactions(driver, cutoff_dt=None, getlimit=9999):
	eles = driver.find_elements(By.XPATH,XP_ACTIVITY_ROW)
	if(getlimit is not None and getlimit > 0):
		eles = eles[0:getlimit]
	print(f"cutoff_dt={cutoff_dt}")
	print(f"max row={len(eles)}")
	for ele in eles:
		txt = ele.text.replace('\n'," | ")
		dt_str = txt.split(' | ')[0]
		row_dt = str_to_dt(dt_str, '%b-%d-%Y').date()
		if(row_dt >= cutoff_dt):
			expand_1_txn(driver,ele,count=5)


def expand_1_txn(driver, ele, count=5):
	for ii in range(0, count):
		try:
			subele = ele.find_elements(By.XPATH, XP_ACT_EXEC_COLLAPSED)
			if len(subele) > 0:
				ele.click()
				force_render(driver)
		except:
			pass


def force_render(driver):
	pass
	#driver.save_screenshot('C:/temp/force_render.png')

def p__process_basic(cells):
	order1 = {}
	order1['Date'] = cells[0]
	order1['Description'] = cells[1]
	order1['Symbol'] = None
	if order1['Description'] is not None:
		order1['Type'] = txn_category(order1['Description'])
		order1['Symbol'] = txn_symbol(order1['Description'])
	order1['Amount'] = cells[2]
	order1['Balance'] = cells[3]
	order1['Details'] = ""
	order1['Price'] = ""
	order1['Shares'] = ""
	order1['Settlement Date'] = ""
	return order1

def p__process_detail(order_text):
	lines = order_text.split("\n")
	if len(lines) <= 2:
		return None
	keys = lines[0::2]
	values = lines[1::2]
	data = {}
	for key, val in zip(keys, values):
		if key == 'Symbol Desc.':
			continue
		data[key] = val
	return data if "Date" in data else None

def p__merge_orders_details(orders,details):
	# --
	# -- indexing
	# --
	details_map = {}
	for detail in details:
		try:
			key = detail['Date'] + detail['Symbol'] + detail['Amount']
			details_map[key] = detail
		except Exception as ex:
			print(f"# WARNING # : building map,detail : {detail}")
			print(type(ex).__name__, ex)
	# --
	for order in orders:
		key = order['Date'] + order['Symbol'] + order['Amount']
		detail = details_map.get(key)
		if(detail is None):
			print(f"# WARNING # : cannot find detail[{key}]")
		else:
			order.update(detail)
	return orders

def raw_transactions(driver, incl_details=True, cutoff_dt=None, cutoff_dt_width=-2, getlimit=9999):
	# --
	# -- cutoff_dt defaults to today() at call time, not at import time
	# --
	if cutoff_dt is None:
		cutoff_dt = today()
	cutoff_dt = days_away(cutoff_dt, cutoff_dt_width)
	def ftr():
		return __impl_raw_transactions(driver, incl_details=incl_details, cutoff_dt=cutoff_dt, getlimit=getlimit)
	return retry(ftr, retry=10, exceptTypes=(StaleElementReferenceException,), rtnEx=False, silent=True)

def __impl_raw_transactions(driver, incl_details=True, cutoff_dt=None, getlimit=9999):
	# --
	# -- expand the list if "Load more results" is available
	# --
	view_all_txns(driver)
	# --
	# -- get txn basic
	# --
	screen_row = driver.find_elements(By.XPATH, XP_ACTIVITY_ROW)
	orders = []
	for order in tqdm(screen_row[0:getlimit], leave=None, desc="txns basic"):
		cells = order.text.split('\n')
		if(len(cells)<=3):
			continue
		order1 = p__process_basic(cells)
		orders.append(order1)

	# --
	# -- get txn details, then merge
	# -- because the basic, detail blocks are not structurally related
	# --
	details = []
	if(incl_details):
		expand_all_transactions(driver,cutoff_dt=cutoff_dt, getlimit=getlimit)
		screen_row = driver.find_elements(By.XPATH, XP_ACTIVITY_DETAIL_ROW)
		for order in tqdm(screen_row, leave=None, desc="txns detail"):
			detail1 = p__process_detail(order.text)
			if(detail1 is not None):
				details.append(detail1)
		orders = p__merge_orders_details(orders,details)
	# --
	# -- prepare dataframe for return
	# --
	df0 = pd.DataFrame(orders)
	df0 = df0.replace("", None)
	non_empty_row = ~df0.isnull().all(axis=1)
	return df0[non_empty_row].sort_values(by=["Date", "Symbol"], ascending=[True, True]).reset_index(drop=True)

def formatted_transactions(raw_txns):
	formatted = raw_txns.copy()
	formatted.rename(columns={'Settlement Date': 'Settlement'}, inplace=True)
	formatted['Type'] = raw_txns['Description'].apply(txn_category)
	formatted['Amount'] = formatted['Amount'].replace("--", "0").replace("[$,]", "", regex=True).astype(float)
	formatted['Shares'] = formatted['Shares'].replace("[$,]", "", regex=True).astype(float)
	formatted['Price'] = formatted['Price'].replace("[$,]", "", regex=True).astype(float)
	formatted['Date'] = formatted['Date'].astype('datetime64[ns]')
	formatted['Settlement'] = formatted['Settlement'].astype('datetime64[ns]')
	formatted = formatted['Type,Date,Symbol,Shares,Price,Amount,Settlement,Description'.split(',')]
	return formatted
