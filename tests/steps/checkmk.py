from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from browser import wait_timeout, load_and_wait


def activate_pending_changes(context):
    load_and_wait(context, "check_mk/wato.py?mode=changelog", "mode=changelog")
    context.browser.find_element(
        By.ID,
        "menu_suggestion_activate_selected"
    ).click()
    WebDriverWait(context.browser, wait_timeout).until(
        lambda browser:
        browser.find_element(
            By.XPATH,
            f"//*[contains(text(), 'Local site monitoring')]/following-sibling::td/following-sibling::td/following-sibling::td"
        ).text.strip() == "0"
    )
