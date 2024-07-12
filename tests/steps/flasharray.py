import logging
import os
import uuid

from behave import *
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

import checkmk
from browser import wait_timeout, load_and_wait
from context import BrowserContext
from purestorage_checkmk_test.flasharray import mock
from purestorage_checkmk_test.flasharray.mock_admin_settings import AdminSettingsContainer
from purestorage_checkmk_test.flasharray.mock_alerts import AlertsContainer
from purestorage_checkmk_test.flasharray.mock_apitokens_container import APITokensContainer
from purestorage_checkmk_test.flasharray.mock_array import ArrayContainer
from purestorage_checkmk_test.flasharray.mock_certificates import CertificatesContainer
from purestorage_checkmk_test.flasharray.mock_controllers import ControllersContainer
from purestorage_checkmk_test.flasharray.mock_dns import DNSServersContainer
from purestorage_checkmk_test.flasharray.mock_drives import DrivesContainer
from purestorage_checkmk_test.flasharray.mock_hardware import HardwaresContainer
from purestorage_checkmk_test.flasharray.mock_smtp import SMTPServersContainer

use_step_matcher("re")


@step("I configured a FlashArray as the \"(?P<hostname>.*)\" host")
def configure_flasharray(context: BrowserContext, hostname: str):
    if hasattr(context, "flasharray"):
        return

    ip = os.getenv("TEST_RUNNER_IP", "192.168.199.1")
    api_token = str(uuid.uuid4())

    context.flasharray_api_tokens_container = APITokensContainer({api_token})
    context.flasharray_drives = DrivesContainer()
    context.flasharray_controllers = ControllersContainer()
    context.flasharray_hardwares = HardwaresContainer(context.flasharray_drives, context.flasharray_controllers)
    context.flasharray_arrays = ArrayContainer()
    context.flasharray_certificates = CertificatesContainer()
    context.flasharray_alerts = AlertsContainer()
    context.flasharray_admin_settings = AdminSettingsContainer()
    context.flasharray_smtp_servers = SMTPServersContainer()
    context.flasharray_dns_servers = DNSServersContainer()

    mock_server = mock.FlashArray(
        api_tokens_container=context.flasharray_api_tokens_container,
        drives_container=context.flasharray_drives,
        controllers_container=context.flasharray_controllers,
        hardwares_container=context.flasharray_hardwares,
        arrays_container=context.flasharray_arrays,
        alerts_container=context.flasharray_alerts,
        certificates_container=context.flasharray_certificates,
        admin_settings_container=context.flasharray_admin_settings,
        smtp_servers_container=context.flasharray_smtp_servers,
        dns_servers_container=context.flasharray_dns_servers,
        cert_ips={"127.0.0.1", "::1", ip},
    )
    context.flasharray = mock_server
    context.flasharray_api_token = api_token
    mock_server.start()
    context.add_cleanup(mock_server.stop)

    # Create a new host
    try:

        load_and_wait(context, f"check_mk/wato.py?folder=&mode=newhost", "mode=newhost")
        context.browser.find_element(By.CSS_SELECTOR, "input[name=\"host\"]").send_keys(
            hostname
        )
        context.browser.find_element(By.CSS_SELECTOR, "label[for=\"cb_host_change_ipaddress\"]").click()
        context.browser.find_element(By.CSS_SELECTOR, "input[name=\"ipaddress\"]").send_keys(ip)
        context.browser.find_element(By.CSS_SELECTOR, "label[for=\"cb_host_change_tag_agent\"]").click()
        context.browser.find_element(By.ID, "select2-tag_agent-container").click()
        context.browser.find_element(By.CSS_SELECTOR, "#select2-tag_agent-results :nth-child(3)").click()
        context.browser.find_element(
            By.CSS_SELECTOR,
            "#suggestions .suggestion.submit a"
        ).click()
    except Exception as e:
        raise AssertionError(f"failed to create FlashArray host: {e}") from e

    # Verify that the FlashArray host exists
    try:
        load_and_wait(context, f"check_mk/wato.py?mode=folder", "mode=folder")
        context.browser.find_element(By.XPATH, f"//*[contains(text(), '{hostname}')]").click()
    except Exception:
        raise AssertionError(f"failed to verify that the host has been created")

    # Create a FlashArray
    try:
        load_and_wait(
            context,
            "check_mk/wato.py?group=datasource_programs&mode=rulesets",
            "group=datasource_programs"
        )
        context.browser.find_element(By.XPATH, "//*[contains(text(), 'Pure Storage FlashArray')]").click()
        WebDriverWait(context.browser, wait_timeout).until(
            ec.url_contains("mode=edit_ruleset")
        )
        context.browser.find_element(By.CSS_SELECTOR, "#suggestions .suggestion a").click()
        WebDriverWait(context.browser, wait_timeout).until(
            ec.url_contains("mode=new_rule")
        )
        context.browser.find_element(By.CSS_SELECTOR, "input[name=\"ve_p_apitoken\"]").send_keys(
            api_token
        )
        cert_field = context.browser.find_element(By.CSS_SELECTOR, "textarea[name=\"ve_p_cert\"]")
        cert_field.send_keys(mock_server.cert().decode('ascii'))

        port_field = context.browser.find_element(By.CSS_SELECTOR, "input[name=\"ve_p_port\"]")
        port_field.clear()
        port_field.send_keys(
            str(mock_server.port())
        )
        context.browser.find_element(
            By.CSS_SELECTOR,
            "label[for=\"cb_explicit_conditions_p_explicit_hosts_USE\"]"
        ).click()
        context.browser.find_element(
            By.ID,
            "select2-explicit_conditions_p_explicit_hosts_0_0-container"
        ).click()
        context.browser.find_element(
            By.ID,
            "select2-explicit_conditions_p_explicit_hosts_0_0-results"
        ).find_element(
            By.XPATH,
            f".//*[contains(text(), '{hostname}')]"
        ).click()
        context.browser.find_element(
            By.CSS_SELECTOR,
            "#suggestions .suggestion.submit a"
        ).click()
        WebDriverWait(context.browser, wait_timeout).until(
            ec.url_contains("mode=edit_ruleset")
        )
    except Exception as e:
        raise AssertionError(f"failed to create FlashArray integration: {e}") from e

    # Apply the changes
    try:
        checkmk.activate_pending_changes(context)
    except Exception as e:
        raise AssertionError(f"failed to create FlashArray integration: {e}") from e

    logging.debug("FlashArray configured")


@given("I added a drive to the FlashArray")
@when("I add a drive to the Flasharray")
def add_drive(context: BrowserContext):
    if not hasattr(context, "flasharray"):
        raise AssertionError("No FlashArray configured")
    context.flasharray_drives.add(1)


@given('I changed drive (?P<drive>\d+) of the FlashArray to be "(?P<status>.*)"')
@when('I change drive (?P<drive>\d+) of the FlashArray to be "(?P<status>.*)"')
def step_impl(context: BrowserContext, drive: str, status: str):
    if not hasattr(context, "flasharray"):
        raise AssertionError("No FlashArray configured")
    context.flasharray_drives.drives[int(drive) - 1].status = status
