from selenium.webdriver.common.by import By

from .crawler_util import *

# --
URL_PAGE = "--n/a--"
XP_MENU_SITE = '//div[@id="pgnb"]/*//ul/li'
PAGE_STATUS_UNKNOWN = "__PAGE_STATUS_UNKNOWN__"
PAGE_STATUS_OK = "__PAGE_STATUS_OK__"


def match(driver):
	return len(driver.find_elements(By.XPATH, XP_MENU_SITE)) > 0


def goto_page(driver):
	goto_url(driver, URL_PAGE, force=True)


def wait_page_loaded(driver, timeout=10):
	wait_for_xpath(driver, XP_MENU_SITE, timeout=timeout)


def page_status(driver):
	label_to_ele = menu_label_map(driver)
	if "LOGOUT" in label_to_ele and "ACCOUNTS&TRADE" in label_to_ele:
		return PAGE_STATUS_OK
	return PAGE_STATUS_UNKNOWN


def menu_label_map(driver):
	label_to_ele = {}
	for ele in driver.find_elements(By.XPATH, XP_MENU_SITE):
		label = ele.text.replace(" ", "").upper().strip()
		if len(label) > 0:
			label_to_ele[label] = ele
	return label_to_ele


def click_menu_label(driver, partial_label):
	for ele in driver.find_elements(By.XPATH, XP_MENU_SITE):
		label = ele.text.replace(" ", "").upper().strip()
		if partial_label.upper() in label:
			ele.click()
			return label
	return None
