from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

def find_element_by_xpath_if_exist(driver,xpath):
	try:
		return driver.find_element_by_xpath(xpath)
	except NoSuchElementException:
		return None

def find_elements_by_xpath_if_exist(driver,xpath):
	try:
		return driver.find_elements_by_xpath(xpath)
	except NoSuchElementException:
		return None

def select_option(select_ele,select_text):
	for option in select_ele.find_elements_by_tag_name('option'):
		if(option.text==select_text):
			option.click()
			return option
	return None

def goto_url(driver,url,force=False,params=None):
	if(params is not None and len(params)!=0):
		url = url.format(*params)
	if( not force and driver.current_url==url ):
		return
	driver.get(url)
	
def click_partial_match(driver,xpath,name):
	elements = driver.find_elements_by_xpath(xpath)
	name = name.upper()
	for ele in elements:
		if(name in ele.text.upper()):
			actual_text = ele.text
			ele.click()
			return ele
	return None

def click(driver,xpath,name):
	elements = driver.find_elements_by_xpath(xpath)
	name = name.upper()
	for ele in elements:
		ele_text = ele.text
		# print("click ... ",ele_text)
		if(ele_text.upper()==name):
			actual_text = ele_text
			ele.click()
			return ele
	return None

def wait_for_xpath(driver,xpath,also_visible=True,timeout=10):
	if(also_visible):
		condition = EC.visibility_of_element_located((By.XPATH,xpath))
		ele_at_xp = WebDriverWait(driver, timeout).until(condition)
		return ele_at_xp
	else:
		condition = EC.presence_of_element_located((By.XPATH,xpath))
		ele_at_xp = WebDriverWait(driver, timeout).until(condition)
		return ele_at_xp

def wait_for_clickable_xpath(driver,xpath,timeout=10):
	condition = EC.element_to_be_clickable((By.XPATH,xpath))
	ele_at_xp = WebDriverWait(driver, timeout).until(condition)
	return ele_at_xp

