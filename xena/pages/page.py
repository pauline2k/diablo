"""
Copyright ©2024. The Regents of the University of California (Regents). All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its documentation
for educational, research, and not-for-profit purposes, without fee and without a
signed licensing agreement, is hereby granted, provided that the above copyright
notice, this paragraph and the following two paragraphs appear in all copies,
modifications, and distributions.

Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
"AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
ENHANCEMENTS, OR MODIFICATIONS.
"""

import time

from flask import current_app as app
from selenium.common import exceptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait as Wait
from xena.test_utils import util


class Page(object):

    def __init__(self, driver, headless):
        self.driver = driver
        self.headless = headless

    PAGE_HEADING = (By.XPATH, '//h1')
    H4_HEADING = (By.XPATH, '//h4')
    DIABLO_FOOTER = (By.ID, 'footer')

    # METHODS TO RETURN SELENIUM ELEMENTS USING A LOCATOR

    def element(self, locator):
        strategy = locator[0]
        target = locator[1]
        if strategy == 'id':
            return self.driver.find_element(By.ID, target)
        elif strategy == 'name':
            return self.driver.find_element(By.NAME, target)
        elif strategy == 'class name':
            return self.driver.find_element(By.CLASS_NAME, target)
        elif strategy == 'link text':
            return self.driver.find_element(By.LINK_TEXT, target)
        elif strategy == 'partial link text':
            return self.driver.find_element(By.PARTIAL_LINK_TEXT, target)
        elif strategy == 'xpath':
            return self.driver.find_element(By.XPATH, target)

    def elements(self, locator):
        strategy = locator[0]
        target = locator[1]
        if strategy == 'id':
            return self.driver.find_elements(By.ID, target)
        elif strategy == 'name':
            return self.driver.find_elements(By.NAME, target)
        elif strategy == 'class name':
            return self.driver.find_elements(By.CLASS_NAME, target)
        elif strategy == 'link text':
            return self.driver.find_elements(By.LINK_TEXT, target)
        elif strategy == 'partial link text':
            return self.driver.find_elements(By.PARTIAL_LINK_TEXT, target)
        elif strategy == 'xpath':
            return self.driver.find_elements(By.XPATH, target)

    # METHODS TO INTERACT WITH ELEMENTS USING A LOCATOR RATHER THAN AN ELEMENT, WHICH HELPS AVOID STALE ELEMENT ERRORS.

    def is_present(self, locator):
        try:
            self.element(locator)
            return True
        except exceptions.NoSuchElementException:
            return False

    def when_present(self, locator, timeout):
        Wait(self.driver, timeout).until(ec.presence_of_element_located(locator))

    def when_not_present(self, locator, timeout):
        tries = 0
        while tries <= timeout:
            tries += 1
            try:
                assert not self.is_present(locator)
                break
            except AssertionError:
                if tries == timeout:
                    raise
                else:
                    time.sleep(1)

    def wait_for_element(self, locator, timeout):
        if util.get_xena_browser() == 'chrome':
            for entry in self.driver.get_log('browser'):
                if app.config['BASE_URL'] in entry:
                    app.logger.warning(f'Console error: {entry}')
        Wait(self.driver, timeout).until(
            method=ec.presence_of_element_located(locator),
            message=f'Failed wait for presence_of_element_located: {str(locator)}',
        )

    def wait_for_text_in_element(self, locator, string):
        tries = 0
        retries = util.get_short_timeout()
        while tries <= retries:
            tries += 1
            try:
                assert string in self.element(locator).get_attribute('innerText')
                break
            except AssertionError:
                if tries == retries:
                    raise
                else:
                    time.sleep(1)

    def wait_for_title_containing(self, string):
        Wait(self.driver, util.get_medium_timeout()).until(ec.title_contains(string))

    def hide_diablo_footer(self):
        if self.is_present(Page.DIABLO_FOOTER) and self.element(Page.DIABLO_FOOTER).is_displayed():
            self.driver.execute_script('document.getElementById("footer").style.display="none";')

    def click_element(self, locator, addl_pause=None):
        self.hide_diablo_footer()
        sleep_default = app.config['CLICK_SLEEP']
        time.sleep(addl_pause or sleep_default)
        try:
            time.sleep(addl_pause or sleep_default)
            self.element(locator).click()
        except (exceptions.ElementClickInterceptedException, exceptions.ElementNotInteractableException) as error:
            app.logger.error(f'Failed to click {locator}, using JS instead - {error}')
            self.click_element_js(locator, addl_pause)

    def click_element_js(self, locator, addl_pause=None):
        sleep_default = app.config['CLICK_SLEEP']
        time.sleep(addl_pause or sleep_default)
        self.driver.execute_script('arguments[0].click();', self.element(locator))

    def wait_for_page_and_click(self, locator, addl_pause=None):
        self.wait_for_element(locator, util.get_medium_timeout())
        self.click_element(locator, addl_pause)

    def wait_for_page_and_click_js(self, locator, addl_pause=None):
        self.when_present(locator, util.get_medium_timeout())
        self.click_element_js(locator, addl_pause)

    def wait_for_element_and_click(self, locator, addl_pause=None):
        self.wait_for_element(locator, util.get_short_timeout())
        self.click_element(locator, addl_pause)

    def wait_for_element_and_type(self, locator, string, addl_pause=None):
        self.wait_for_element_and_click(locator, addl_pause)
        self.element(locator).clear()
        self.element(locator).send_keys(string)

    def wait_for_element_and_type_js(self, element_id, string, addl_pause=None):
        self.wait_for_page_and_click_js((By.ID, element_id), addl_pause)
        self.driver.execute_script(f"document.getElementById('{element_id}').value='{string}'")

    def remove_chars(self, locator):
        self.wait_for_element_and_click(locator)
        repeat = 300
        for x in range(repeat):
            self.hit_delete()
            self.hit_backspace()

    def enter_chars(self, locator, string):
        for i in string:
            time.sleep(0.5)
            self.element(locator).send_keys(i)

    def remove_and_enter_chars(self, locator, string):
        self.remove_chars(locator)
        self.element(locator).send_keys(string)

    # PAGE TITLE AND HEADING

    def title(self):
        return self.driver.title

    def wait_for_title(self, string):
        app.logger.info(f"'Waiting for page title '{string}'")
        Wait(self.driver, util.get_short_timeout()).until(
            method=(ec.title_contains(string)),
            message=f'Failed wait_for_title: {string}',
        )

    def wait_for_title_contains(self, string):
        app.logger.info(f"Waiting for page title containing '{string}")
        Wait(self.driver, util.get_short_timeout()).until(
            method=(ec.title_contains(string)),
            message=f'Failed wait_for_title_contains: {string}',
        )

    def visible_heading(self):
        return self.element(Page.PAGE_HEADING).text

    def visible_h4_heading(self):
        return self.driver(Page.H4_HEADING).text

    # NAVIGATION AND KEYSTROKES

    def reload_page(self):
        self.driver.refresh()

    def scroll_to_top(self):
        self.driver.execute_script('window.scrollTo(0, 0);')

    def scroll_to_bottom(self):
        self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')

    def mouseover(self, element):
        ActionChains(self.driver).move_to_element(element).perform()

    def hit_enter(self):
        ActionChains(self.driver).send_keys(Keys.ENTER).perform()

    def hit_escape(self):
        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()

    def hit_delete(self):
        ActionChains(self.driver).send_keys(Keys.DELETE).perform()

    def hit_backspace(self):
        ActionChains(self.driver).send_keys(Keys.BACKSPACE).perform()

    # EXTERNAL LINK VALIDATOR

    def window_handles(self):
        return self.driver.window_handles

    def switch_to_last_window(self, windows):
        self.driver.switch_to.window(windows[-1])

    def close_window_and_switch(self):
        if len(self.window_handles()) > 1:
            self.driver.close()
            self.driver.switch_to.window(self.window_handles()[0])
        else:
            app.logger.info('Only one window is open, not closing it')

    def external_link_valid(self, locator, expected_page_title):
        self.wait_for_element_and_click(locator)
        time.sleep(1)
        try:
            windows = self.window_handles()
            if len(windows) > 1:
                self.switch_to_last_window(windows)
                self.wait_for_title(expected_page_title)
                app.logger.info(f'Found new window with title "{expected_page_title}"')
                return True
            else:
                app.logger.info('Link did not open in a new window')
                app.logger.info(
                    f'Expecting page title {expected_page_title}, but visible page title is {self.driver.title()}')
                return False
        finally:
            self.close_window_and_switch()

    @staticmethod
    def assert_equivalence(actual, expected):
        if actual != expected:
            app.logger.info(f'Expecting {expected}, got {actual}')
        assert actual == expected
