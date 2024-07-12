import logging
import os
import uuid

from behave import *
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

import checkmk
import purestorage_checkmk_test.flashblade.mock_blades
from browser import wait_timeout, load_and_wait
from context import BrowserContext
from purestorage_checkmk_test.flashblade import mock
from purestorage_checkmk_test.flashblade.mock_apitokens_container import APITokensContainer
from purestorage_checkmk_test.flashblade.mock_array import ArraysContainer
from purestorage_checkmk_test.flashblade.mock_support import SupportContainer

use_step_matcher("re")


@step("I configured a FlashBlade as the \"(?P<hostname>.*)\" host")
def configure_flashblade(context: BrowserContext, hostname: str):
    if hasattr(context, "flashblade"):
        return

    ip = os.getenv("TEST_RUNNER_IP", "192.168.199.1")
    api_token = str(uuid.uuid4())
    blades = purestorage_checkmk_test.flashblade.mock_blades.BladesContainer()
    hardware = purestorage_checkmk_test.flashblade.mock.HardwareContainer(blades)
    alerts = purestorage_checkmk_test.flashblade.mock.AlertsContainer()
    arrays_space = purestorage_checkmk_test.flashblade.mock.ArraysSpaceContainer()
    certificates = purestorage_checkmk_test.flashblade.mock.CertificatesContainer()
    network_interfaces = purestorage_checkmk_test.flashblade.mock.NetworkInterfaceContainer()
    arrays = ArraysContainer()
    support = SupportContainer()
    api_tokens_container = APITokensContainer({api_token})
    mock_server = mock.FlashBlade(
        api_tokens_container=api_tokens_container,
        blades_container=blades,
        hardware_container=hardware,
        alerts_container=alerts,
        arrays_space_container=arrays_space,
        certificates_container=certificates,
        network_interfaces_container=network_interfaces,
        arrays_container=arrays,
        support_container=support,
        cert_ips={"127.0.0.1", "::1", ip}
    )
    context.flashblade_blades = blades
    context.flashblade_hardware = hardware
    context.flashblade = mock_server
    context.flashblade_api_token = api_token
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
        raise AssertionError(f"failed to create FlashBlade host: {e}") from e

    # Verify that the FlashBlade host exists
    try:
        load_and_wait(context, f"check_mk/wato.py?mode=folder", "mode=folder")
        context.browser.find_element(By.XPATH, f"//*[contains(text(), '{hostname}')]").click()
    except Exception:
        raise AssertionError(f"failed to verify that the host has been created")

    # Create a FlashBlade
    try:
        load_and_wait(
            context,
            "check_mk/wato.py?group=datasource_programs&mode=rulesets",
            "group=datasource_programs"
        )
        context.browser.find_element(By.XPATH, "//*[contains(text(), 'Pure Storage FlashBlade')]").click()
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

        for element in context.browser.find_elements(By.CSS_SELECTOR, ".nform .show_more"):
            # noinspection PyBroadException
            try:
                element.click()
            except:
                pass

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
        raise AssertionError(f"failed to create FlashBlade integration: {e}") from e

    # Apply the changes
    try:
        checkmk.activate_pending_changes(context)
    except Exception as e:
        raise AssertionError(f"failed to create FlashBlade integration: {e}") from e

    logging.debug("FlashBlade configured")


@given("I added a blade to the FlashBlade")
@when("I add a blade to the FlashBlade")
def add_blade(context: BrowserContext):
    if not hasattr(context, "flashblade"):
        raise AssertionError("No FlashBlade configured")
    context.flashblade_blades.add(10)


@given('I changed blade (?P<blade>\d+) of the FlashBlade to be "(?P<status>.*)"')
@when('I change blade (?P<blade>\d+) of the FlashBlade to be "(?P<status>.*)"')
def step_impl(context: BrowserContext, blade: str, status: str):
    if not hasattr(context, "flashblade"):
        raise AssertionError("No FlashBlade configured")
    context.flashblade_blades.blades[int(blade) - 1].status = status
