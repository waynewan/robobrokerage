from selenium.webdriver.common.by import By

from .crawler_util import *

# --
URL_PAGE = "https://digital.fidelity.com/ftgw/digital/portfolio/summary"
XP_PAGE_ID1 = '//button[@aria-label="customize cards"]'
XP_LEGACY_PAGE_BTN = '//a[text()="legacy portfolio summary page"]'
PAGE_STATUS_UNKNOWN = "__PAGE_STATUS_UNKNOWN__"
PAGE_STATUS_OK = "__PAGE_STATUS_OK__"


def match(driver):
	return len(driver.find_elements(By.XPATH, XP_PAGE_ID1)) > 0


def goto_page(driver):
	goto_url(driver, URL_PAGE, force=True)


def wait_page_loaded(driver, timeout=10):
	wait_for_clickable_xpath(driver, XP_PAGE_ID1, timeout=timeout)


def page_status(driver):
	cur_tab_ele = driver.find_elements(By.XPATH, XP_PAGE_ID1)
	if len(cur_tab_ele) > 0:
		return PAGE_STATUS_OK
	return PAGE_STATUS_UNKNOWN


def goto_legacy(driver):
	try:
		legacy_btn = driver.find_element(By.XPATH, XP_LEGACY_PAGE_BTN)
		legacy_btn.click()
		return True
	except:
		return False
