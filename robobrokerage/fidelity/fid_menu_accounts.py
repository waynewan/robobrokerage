from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By

from .crawler_util import *
from jackutil.microfunc import retry

# --
URL_PAGE = "--n/a--"
XP_MENU_ACCOUNTS = '//a[@class="pvd-link__link"]'
PAGE_STATUS_UNKNOWN = "__PAGE_STATUS_UNKNOWN__"
PAGE_STATUS_OK = "__PAGE_STATUS_OK__"


def match(driver):
	return len(driver.find_elements(By.XPATH, XP_MENU_ACCOUNTS)) > 0


def goto_page(driver):
	goto_url(driver, URL_PAGE, force=True)


def wait_page_loaded(driver, timeout=10):
	wait_for_xpath(driver, XP_MENU_ACCOUNTS, also_visible=False, timeout=timeout)


def page_status(driver):
	label_to_ele = account_label_map(driver)
	if len(label_to_ele) > 0:
		return PAGE_STATUS_OK
	return PAGE_STATUS_UNKNOWN


def account_label_map(driver):
	label_to_ele = {}
	for ele in driver.find_elements(By.XPATH, XP_MENU_ACCOUNTS):
		pvd_id = ele.get_attribute("id")
		ele_text = ele.text
		if ele_text is None:
			continue
		if pvd_id in ele_text:
			label_to_ele[pvd_id] = ele
	return label_to_ele


def __impl_select_account(driver, partial_label):
	for ele in driver.find_elements(By.XPATH, XP_MENU_ACCOUNTS):
		pvd_id = ele.get_attribute("id")
		ele_text = ele.text
		if ele_text is None:
			continue
		if pvd_id not in ele_text:
			continue
		if partial_label.upper() in ele_text.upper():
			ele.click()
			return ele_text
	return False


def select_account(driver, partial_label):
	if partial_label is None:
		raise ValueError("partial_label cannot be None")
	def ftr():
		return __impl_select_account(driver, partial_label)
	return retry(ftr, retry=10, exceptTypes=(StaleElementReferenceException,), rtnEx=False, silent=True)
