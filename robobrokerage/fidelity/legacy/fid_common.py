from ..crawler_util import *
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from collections import defaultdict
import time

URL_ACTIVITIES_AND_ORDERS = 'https://oltx.fidelity.com/ftgw/fbc/oftop/portfolio#activity'
XPATH_PROGRESS_POPUP = '/html/body/div[@class="progress-bar bordered"][@style="display: none;"]'
XPATH_ORDERS_ACTION_BTNS = '//*[@id="orderExpanderContent"]//table//button'
XPATH_ACC_SELECTOR_MAIN_CHILDREN = '//div[@class="account-selector--main-wrapper"]//div'
#//
URL_POSITIONS = 'https://oltx.fidelity.com/ftgw/fbc/oftop/portfolio#positions'

def text_to_map(text):
	item = text.split('\n')
	keys = item[0::2]
	vals = item[1::2]
	return { key:val for key,val in zip(keys,vals) }

def wait_for_xpath(driver,xpath,timeout=10):
	expected_cond = EC.presence_of_element_located((
		By.XPATH,
		xpath
	))
	block_popup = WebDriverWait(driver, timeout).until(expected_cond)
	return block_popup

def wait_for_block_popup_close(driver,timeout=10):
	expected_cond = EC.presence_of_element_located((
		By.XPATH,
		XPATH_PROGRESS_POPUP
	))
	block_popup = WebDriverWait(driver, timeout).until(expected_cond)
	return block_popup

def scroll_to_xpath(driver,xpath):
	element = driver.find_element(By.XPATH, xpath)
	driver.execute_script("arguments[0].scrollIntoView();", element)

def extract_button_info(btn):
	ID = btn.get_attribute('id')
	url = btn.get_attribute('url')
	if(ID=='cancelBtn'):
		pp = url.index('ORDER_NUM')
		ordnum = url[pp+10:pp+18]
		return (ID,ordnum)
	elif(ID=='cancelRepBtn'):
		pp = url.index('CANCELLED_ORDER_NUMBER')
		ordnum = url[pp+23:pp+31]
		return (ID,ordnum)

def create_ordnum_button_map(driver):
	ordnum_to_actions = defaultdict(lambda: {})
	buttons = driver.find_elements_by_xpath(XPATH_ORDERS_ACTION_BTNS)
	for btn in buttons:
		action,ordnum = extract_button_info(btn)
		ordnum_to_actions[ordnum][action] = btn
	return ordnum_to_actions

def goto_positions_all_accounts(driver):
	goto_url(driver,URL_POSITIONS,force=True)
	time.sleep(1)
	wait_for_block_popup_close(driver,timeout=10)
	side_panel_select_account(driver,"All Accounts")

def goto_expanded_orders(driver):
	goto_url(driver,URL_ACTIVITIES_AND_ORDERS,force=True)
	wait_for_block_popup_close(driver,timeout=10)
	click(driver,'//*[@id="tabContentActivity"]//*[contains(text(),"Orders")]','Orders')
	wait_for_block_popup_close(driver,timeout=10)
	click(driver,'//*[@id="orderExpanderContent"]//a',"Expand all")
	wait_for_block_popup_close(driver,timeout=10)

def goto_collapse_orders(driver):
	goto_url(driver,URL_ACTIVITIES_AND_ORDERS)
	wait_for_block_popup_close(driver,timeout=10)
	click(driver,'//*[@id="orderExpanderContent"]//a',"Collapse all")

def goto_expanded_history(driver,days_opt='90'):
	goto_url(driver,'https://oltx.fidelity.com/ftgw/fbc/oftop/portfolio#activity',force=True)
	wait_for_block_popup_close(driver,timeout=10)
	click(driver,'//*[@id="tabContentActivity"]//*[contains(text(),"History")]','History')
	wait_for_block_popup_close(driver,timeout=10)
	click_partial_match(driver,'//*[@id="activity--history-range-dropdown"]//option',days_opt)
	wait_for_block_popup_close(driver,timeout=10)
	click(driver,'//*[@id="historyExpanderContent"]//a',"Expand all")
	wait_for_block_popup_close(driver,timeout=10)

def ping(self):
	goto_url(self.driver,URL_ACTIVITIES_AND_ORDERS,force=True)

# --
# -- account, case insensitive, can be partial
# --
def side_panel_select_account(driver,account):
	children = driver.find_elements_by_xpath(XPATH_ACC_SELECTOR_MAIN_CHILDREN)
	account = account.upper()
	for child in children:
		lines = child.text.split('\n')
		if(len(lines)==0):
			continue
		if(account in lines[0].upper()):
			child.click()
			time.sleep(1)
			wait_for_block_popup_close(driver,timeout=10)
			return True
	return False
	
