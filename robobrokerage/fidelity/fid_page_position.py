from selenium.webdriver.common.by import By

from .crawler_util import *

import pandas as pd
import numpy as np
import re
import locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF8')

# --
URL_PAGE = "https://digital.fidelity.com/ftgw/digital/portfolio/positions"
XP_OVERVIEW_TAB = '//option[text()="Overview"]'
XP_REFRESH = '//div[@id="posweb-grid_top"]//button[@aria-label="Refresh Positions"]'
XP_POSITION_TABLE_HEADER = '//div[@id="posweb-grid"]//*[@role="columnheader"]'
XP_POSITION_TABLE_DATA = '//div[@id="posweb-grid"]//*[@role="rowgroup"]/*[@role="row"][@row-index]'
PAGE_STATUS_UNKNOWN = "__PAGE_STATUS_UNKNOWN__"
PAGE_STATUS_OK = "__PAGE_STATUS_OK__"


def match(driver):
	return len(driver.find_elements(By.XPATH, XP_OVERVIEW_TAB)) > 0


def goto_page(driver):
	goto_url(driver, URL_PAGE, force=True)


def wait_page_loaded(driver, timeout=300):
	wait_for_clickable_xpath(driver, XP_OVERVIEW_TAB, timeout=timeout)
	wait_for_xpath(driver, XP_POSITION_TABLE_DATA, timeout=timeout)


def page_status(driver):
	cur_tab_ele = driver.find_elements(By.XPATH, XP_OVERVIEW_TAB)
	if len(cur_tab_ele) > 0:
		return PAGE_STATUS_OK
	return PAGE_STATUS_UNKNOWN


# --
# -- actions
# --
def select_overview_tab(driver):
	pos_view_select = driver.find_element(By.XPATH, XP_OVERVIEW_TAB + "/parent::select")
	select_option_relax(pos_view_select, "Overview")


def select_dividend_view_tab(driver):
	pos_view_select = driver.find_element(By.XPATH, XP_OVERVIEW_TAB + "/parent::select")
	select_option_relax(pos_view_select, "Dividend")


def select_closed_positions_tab(driver):
	pos_view_select = driver.find_element(By.XPATH, XP_OVERVIEW_TAB + "/parent::select")
	select_option_relax(pos_view_select, "Closed")


def select_fund_performance_tab(driver):
	pos_view_select = driver.find_element(By.XPATH, XP_OVERVIEW_TAB + "/parent::select")
	select_option_relax(pos_view_select, "Perform")


def select_refresh_positions(driver):
	driver.find_element(By.XPATH, XP_REFRESH).click()


def raw_header(driver):
	return [ele.text for ele in driver.find_elements(By.XPATH, XP_POSITION_TABLE_HEADER)]


def raw_data(driver, header=None):
	data_eles = driver.find_elements(By.XPATH, XP_POSITION_TABLE_DATA)
	rows = []
	for ele in data_eles:
		rowindex = int(ele.get_attribute("row-index"))
		row = [cell.text for cell in ele.find_elements(By.XPATH, ".//*[@comp-id]")]
		if rowindex >= len(rows):
			rows.append(row)
		else:
			rows[rowindex] = [*rows[rowindex], *row]
	if header is None:
		return rows
	df0 = pd.DataFrame(rows)
	df0.columns = header
	return df0


def expand_position_table(df0):
	dfs = [
		process_simple_col(df0['Symbol'], header='Symbol,Desc,__IGNORE__'),
		process_simple_col(df0['Last price'], header='Last Price'),
		process_simple_col(df0['Last price change'], header='Price Change'),
		process_simple_col(df0["Today's gain/loss $"], header='$ Gain/Loss'),
		process_simple_col(df0["Today's gain/loss %"], header='% Gain/Loss'),
		process_simple_col(df0['Total gain/loss $'], header='$ Total Gain/Loss'),
		process_simple_col(df0['Total gain/loss %'], header='% Total Gain/Loss'),
		process_simple_col(df0['Current value'], header='Current Value'),
		process_simple_col(df0['% of account'], header='% of Account'),
		process_simple_col(df0['Quantity'], header='Quantity'),
		process_simple_col(df0['Average cost basis'], header='Per Share'),
		process_simple_col(df0['Cost basis total'], header='Total Cost'),
		process_simple_col(df0['52-week range'], header='52w lo,52w hi'),
	]
	df1 = pd.concat(dfs, axis=1)
	df1.drop(columns=['__IGNORE__'], inplace=True)
	return df1


def process_simple_col(series, header=None):
	df0 = pd.DataFrame(series.str.split('\n').tolist())
	if header is not None:
		if type(header) == str:
			header = header.split(',')
		if len(df0.columns) != len(header):
			print(f"WARN: df0,header count mismatch: force matching: was (header,df0.columns)=({header},{list(df0.columns)})")
			df0 = df0.iloc[:, 0:len(header)]
		df0.columns = header
	return df0


def format_val_remove_char(rm_regex, defVal=np.nan):
	def ff(colval):
		if colval is None:
			return defVal
		return rm_regex.sub('', colval)
	return ff


def format_col_to_numeric(colval, rm_fn=format_val_remove_char(re.compile(r'[$,%]'))):
	if colval is None:
		return np.nan
	if type(colval) == type(np.nan):
		return colval
	if '--' in colval:
		return np.nan
	try:
		return float(rm_fn(colval))
	except:
		print("##### ERR/NOT_FLOAT", colval)
		return np.nan


def format_position_table(data):
	data = data.copy()
	data.fillna(np.nan, inplace=True)
	data.replace("n/a", np.nan, inplace=True)
	data.replace("--", np.nan, inplace=True)
	data.replace("", np.nan, inplace=True)
	# --
	# !! explicit per-column (not a loop) to make debugging easier !!
	# --
	data['Last Price'] = data['Last Price'].apply(format_col_to_numeric)
	data['Price Change'] = data['Price Change'].apply(format_col_to_numeric)
	data['$ Gain/Loss'] = data['$ Gain/Loss'].apply(format_col_to_numeric)
	data['% Gain/Loss'] = data['% Gain/Loss'].apply(format_col_to_numeric)
	data['$ Total Gain/Loss'] = data['$ Total Gain/Loss'].apply(format_col_to_numeric)
	data['% Total Gain/Loss'] = data['% Total Gain/Loss'].apply(format_col_to_numeric)
	data['Current Value'] = data['Current Value'].apply(format_col_to_numeric)
	data['% of Account'] = data['% of Account'].apply(format_col_to_numeric)
	data['Quantity'] = data['Quantity'].apply(format_col_to_numeric)
	data['Per Share'] = data['Per Share'].apply(format_col_to_numeric)
	data['Total Cost'] = data['Total Cost'].apply(format_col_to_numeric)
	data['52w lo'] = data['52w lo'].apply(format_col_to_numeric)
	data['52w hi'] = data['52w hi'].apply(format_col_to_numeric)
	return data
