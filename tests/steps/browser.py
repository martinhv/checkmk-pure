import time
from urllib.parse import quote_plus

import selenium.common.exceptions
from behave import *
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox import webdriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

import checkmk
from steps.context import BrowserContext

use_step_matcher("re")

wait_timeout = 30


def load_and_wait(context: BrowserContext, url: str, url_fragment: str):
    context.browser.get(context.endpoint + url)

    def predicate(browser: webdriver.WebDriver):
        if url_fragment not in browser.current_url:
            return False
        page_state = browser.execute_script('return document.readyState;')
        return page_state == 'complete'

    WebDriverWait(context.browser, wait_timeout).until(predicate)


@given("I logged in")
def login(context: BrowserContext):
    try:
        load_and_wait(context, "check_mk/login.py", "login.py")
        context.browser.find_element(By.ID, "input_user").send_keys(context.user)
        context.browser.find_element(By.ID, "input_pass").send_keys(context.password)
        context.browser.find_element(By.ID, "_login").click()
        WebDriverWait(context.browser, wait_timeout).until(
            ec.url_contains(context.endpoint + "check_mk/index.py")
        )
    except Exception as e:
        raise AssertionError(f"login failed: {e}") from e


@when('I navigate to the "(?P<page>.*)" page')
def navigate_to(context: BrowserContext, page: str):
    pagemap = {
        "All hosts": "check_mk/view.py?view_name=allhosts",
        "Other integrations": "check_mk/wato.py?group=datasource_programs&mode=rulesets"
    }

    url = pagemap[page]
    try:
        load_and_wait(context, url, url)
    except Exception as e:
        raise AssertionError(f"failed to load {url}: {e}") from e


@then('I should see "(?P<text>.*)"')
def see_text(context: BrowserContext, text: str):
    try:
        context.browser.find_element(By.XPATH, "//*[contains(text(), '" + text + "')]")
    except Exception as e:
        raise AssertionError(f"no element containing the text {text} was found: {e}") from e


@then("I should see (?P<count>\d+) services")
def see_services(context: BrowserContext, count: str):
    if "view_name=host" not in context.browser.current_url:
        raise AssertionError("cannot look for services, not on a host page")
    # We add one row to account for the header Checkmk adds.
    assert len(context.browser.find_elements(By.CSS_SELECTOR, "table.data tbody tr")) == int(count) + 1


@then("I should see at least (?P<count>\d+) services")
def see_services(context: BrowserContext, count: str):
    if "view_name=host" not in context.browser.current_url:
        raise AssertionError("cannot look for services, not on a host page")
    # We add one row to account for the header Checkmk adds.
    assert len(context.browser.find_elements(By.CSS_SELECTOR, "table.data tbody tr")) >= int(count) + 1


@then('I should see a service titled "(?P<service>.*)"')
def not_see_service(context: BrowserContext, service: str):
    context.service = service
    if "view_name=host" not in context.browser.current_url:
        raise AssertionError("cannot look for services, not on a host page")
    try:
        context.service_row = context.browser.find_element(
            By.XPATH,
            "//table[@class='data']//tbody//tr//td[2]//*[contains(text(), '" + service + "')]/parent::td/parent::tr"
        )
    except selenium.common.exceptions.NoSuchElementException:
        raise AssertionError(f"no service named {service} found ")


@then('I should not see a service titled "(?P<service>.*)"')
def not_see_service(context: BrowserContext, service: str):
    context.service = service
    if "view_name=host" not in context.browser.current_url:
        raise AssertionError("cannot look for services, not on a host page")
    try:
        context.browser.find_element(
            By.XPATH,
            "//table[@class='data']//tbody//tr//td[2]//*[contains(text(), '" + service + "')]"
        )
        raise AssertionError(f"found service named {service}")
    except selenium.common.exceptions.NoSuchElementException:
        pass


@when("I open the services of the \"(.*)\" host")
def open_host_services(context: BrowserContext, hostname: str):
    load_and_wait(context,
                  f"check_mk/view.py?host={quote_plus(hostname)}&site={quote_plus(context.site_name)}&view_name=host",
                  "view_name=host")
    context.hostname = hostname


@given("I ran the service discovery for the \"(?P<hostname>.*)\" host")
@when("I run the service discovery for the \"(?P<hostname>.*)\" host")
def run_sd(context: BrowserContext, hostname: str):
    context.hostname = hostname
    load_and_wait(context, f"check_mk/wato.py?folder=&host={quote_plus(hostname)}&mode=inventory", "mode=inventory")
    found = False
    for i in range(1, 5):
        try:
            WebDriverWait(context.browser, wait_timeout).until(
                lambda browser:
                "disabled" not in browser.find_element(
                    By.ID,
                    "menu_suggestion_refresh"
                ).find_element(
                    By.XPATH,
                    ".."
                ).get_attribute("class")
            )
            found = True
            break
        except selenium.common.exceptions.StaleElementReferenceException:
            pass
        except selenium.common.exceptions.TimeoutException:
            pass
    if not found:
        time.sleep(600)
        raise AssertionError("Failed to wait for service discovery to become available.")
    context.browser.find_element(
        By.ID,
        "menu_suggestion_refresh"
    ).click()
    # Wait until the async message is shown
    WebDriverWait(context.browser, wait_timeout).until(
        lambda browser:
        context.browser.execute_script(
            'return window.getComputedStyle(arguments[0], null).display;',
            context.browser.find_element(
                By.ID,
                "async_progress_msg"
            )) != 'none'
    )
    # Wait until the async message disappears
    WebDriverWait(context.browser, wait_timeout).until(
        lambda browser:
        context.browser.execute_script(
            'return window.getComputedStyle(arguments[0], null).display;',
            context.browser.find_element(
                By.ID,
                "async_progress_msg"
            )) == 'none'
    )


@given('I rescheduled the "(?P<service>.*)" service on the "(?P<hostname>.*)" host')
@when('I reschedule the "(?P<service>.*)" service on the "(?P<hostname>.*)" host')
def reschedule_service(context: BrowserContext, service: str, hostname: str):
    context.hostname = hostname
    context.service = service
    load_and_wait(
        context,
        f"check_mk/view.py?host={quote_plus(hostname)}&service={quote_plus(service)}&site={quote_plus(context.site_name)}&view_name=service",
        "view_name=service"
    )
    found = False
    for i in range(1, wait_timeout):
        try:
            reschedule_link = context.browser.find_element(By.CSS_SELECTOR, "#popup_trigger_action_menu a")
            reschedule_link.click()
            found = True
            break
        except selenium.common.exceptions.NoSuchElementException:
            time.sleep(1)
    if not found:
        raise AssertionError("Failed to find popup trigger button.")
    context.browser.find_element(
        By.ID,
        "popup_menu"
    ).find_element(
        By.XPATH,
        ".//*[contains(text(), 'Reschedule')]"
    ).click()
    WebDriverWait(context.browser, wait_timeout).until(
        lambda browser: "reloading" not in browser.find_element(
            By.CSS_SELECTOR,
            "#popup_trigger_action_menu a img"
        ).get_attribute("class")
    )


@given('I waited for the "(?P<service>.*)" service on the "(?P<hostname>.*)" host to be "(?P<status>.*)"')
@when('I wait for the "(?P<service>.*)" service on the "(?P<hostname>.*)" host to be "(?P<status>.*)"')
def wait_for_service_status(context: BrowserContext, service: str, hostname: str, status: str):
    context.hostname = hostname
    context.service = service
    load_and_wait(
        context,
        f"check_mk/view.py?host={quote_plus(hostname)}&service={quote_plus(service)}&site={quote_plus(context.site_name)}&view_name=service",
        "view_name=service"
    )
    found = False
    for i in range(1, int(wait_timeout / 5)):
        if context.browser.find_element(By.CSS_SELECTOR, ".svcstate").get_attribute("innerText") == status:
            found = True
            break
        time.sleep(5)
        context.browser.refresh()
    if not found:
        raise AssertionError(f"service failed to enter the {status} state")


@given('I monitored undecided services on the "(?P<hostname>.*)" host')
@when('I monitor undecided services on the "(?P<hostname>.*)" host')
def monitor_undecided_services(context: BrowserContext, hostname: str):
    context.hostname = hostname

    found = False
    for i in range(1, wait_timeout):
        load_and_wait(context, f"check_mk/wato.py?folder=&host={quote_plus(hostname)}&mode=inventory", "mode=inventory")
        # noinspection PyBroadException
        try:
            try:
                WebDriverWait(context.browser, wait_timeout).until(
                    lambda browser:
                    "display" in context.browser.find_element(
                        By.ID,
                        "async_progress_msg"
                    ).get_attribute("style")
                )
            except selenium.common.exceptions.NoSuchElementException:
                pass
            for j in range(1, 10):
                try:
                    context.browser.find_element(By.ID, "form_checks_new")
                    found = True
                    break
                except selenium.common.exceptions.NoSuchElementException:
                    time.sleep(1)
            if found:
                break
        except Exception as e:
            time.sleep(5)
    if not found:
        raise AssertionError("No undecided services were found.")
    monitor_button = context.browser.find_element(
        By.ID,
        "menu_suggestion_bulk_new_old"
    )
    monitor_button.click()
    WebDriverWait(context.browser, wait_timeout).until(
        lambda browser: "disabled" in context.browser.find_element(
            By.ID,
            "menu_suggestion_bulk_new_old"
        ).find_element(
            By.XPATH,
            "./parent::div"
        ).get_attribute("class")
    )
    checkmk.activate_pending_changes(context)


@step('that service should be "(?P<status>.*)"')
def service_should_be_healthy(context: BrowserContext, status: str):
    if not hasattr(context, "service_row"):
        raise AssertionError("no previous query for the service is present")
    status_field = context.service_row.find_element(By.CSS_SELECTOR, "td:nth-child(1)")
    status_field_text = status_field.get_attribute("innerText")
    assert status_field_text == status, f"Incorrect status: {status_field_text}"


@then('the service should eventually be "(?P<status>.*)"')
def service_should_eventually_be(context: BrowserContext, status: str):
    if not hasattr(context, "service"):
        raise AssertionError("no previous query for the service is present")
    if not hasattr(context, "hostname"):
        raise AssertionError("no previous query for the hostname is present")
    load_and_wait(
        context,
        f"check_mk/view.py?host={quote_plus(context.hostname)}&service={quote_plus(context.service)}&site={quote_plus(context.site_name)}&view_name=service",
        "view_name=service"
    )
    found = False
    for i in range(1, int(wait_timeout / 5)):
        if context.browser.find_element(By.CSS_SELECTOR, ".svcstate").get_attribute("innerText") == status:
            found = True
            break
        time.sleep(5)
        context.browser.refresh()
    if not found:
        raise AssertionError(f"service failed to enter the {status} state")
