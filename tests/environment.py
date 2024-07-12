import logging
import os
import re
import subprocess

from behave import runner
from behave.capture import Captured
from behave.model import Feature, Scenario, Step
from behave.model_core import Status
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

summary = ""
feature_count = 0
scenario_count = 0


def before_all(context: runner.Context):
    global summary
    global feature_count
    feature_count = 0
    summary = ""
    context.site_name = os.getenv("CHECKMK_SITE_NAME", "monitoring")


def after_all(context: runner.Context):
    global summary
    global feature_count
    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_file is not None and summary_file != "":
        with open(summary_file, "w") as f:
            f.write(summary)


def before_feature(context: runner.Context, feature: Feature):
    global summary, feature_count, scenario_count
    feature_count = feature_count + 1
    scenario_count = 0
    summary = summary + f"## {feature.name}\n\n"


def after_feature(context: runner.Context, feature: Feature):
    pass


def before_scenario(context: runner.Context, scenario: Scenario):
    global summary, feature_count, scenario_count
    summary = summary + f"### {scenario.name}\n\n"
    scenario_count = scenario_count + 1
    context.step_count = 0

    endpoint = get_config("HTTP_ENDPOINT", "http://127.0.0.1:8080/")
    checkmk_site_name = get_config("CHECKMK_SITE_NAME", "monitoring")
    checkmk_site_user = get_config("CHECKMK_SITE_USER", "cmkadmin")
    checkmk_site_password = get_config("CHECKMK_SITE_PASSWORD", "test")
    container_start = get_config("CONTAINER_START", "1")
    up_command = get_config("CONTAINER_UP_COMMAND", "docker compose up -d --wait checkmk")
    geckodriver_path = get_config("GECKODRIVER_PATH", "/snap/bin/geckodriver")
    display = os.getenv("DISPLAY")
    if display is None or display == "":
        headless = get_config("HEADLESS", "1")
    else:
        headless = get_config("HEADLESS", "0")

    if container_start:
        process = subprocess.run(up_command, shell=True, capture_output=True, text=True)
        if process.returncode != 0:
            import sys
            sys.stdout.write(process.stdout)
            sys.stderr.write(process.stderr)
            raise Exception(f"Test container failed to start (exit code {process.returncode}")
    options = Options()
    options.headless = headless == "1"
    context.browser = webdriver.Firefox(
        executable_path=geckodriver_path,
        options=options,
    )
    context.endpoint = endpoint + checkmk_site_name + "/"
    context.user = checkmk_site_user
    context.password = checkmk_site_password


def after_scenario(context: runner.Context, scenario: Scenario):
    container_stop = get_config("CONTAINER_STOP", "1")
    if context.browser is not None:
        context.browser.quit()
    if container_stop:
        down_command = get_config("CONTAINER_DOWN_COMMAND", "docker compose down -t 1")
        process = subprocess.run(down_command, shell=True, capture_output=True, text=True)
        if process.returncode != 0:
            import sys
            sys.stdout.write(process.stdout)
            sys.stderr.write(process.stderr)
            raise Exception(f"Test container failed to start (exit code {process.returncode}")


def before_step(context: runner.Context, step: Step):
    context.step_count = context.step_count + 1


def after_step(context: runner.Context, step: Step):
    global summary, feature_count, scenario_count

    screenshot_path = f"screenshots/{feature_count}-{urlize(context.feature.name)}/{scenario_count}-{urlize(context.scenario.name)}/{context.step_count}-{urlize(step.name)}.png"
    os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
    summary = summary + f"<details><summary>{step.name} ({step.status.name})</summary>\n\n"
    if step.status == Status.failed:
        summary = summary + str(step.exception)
    else:
        captured: Captured = step.captured
        summary = summary + captured.output
    summary += "</details>\n\n"

    if context.browser.save_screenshot(screenshot_path):
        logging.debug(f"Saved screenshot as {screenshot_path}")
    else:
        logging.debug(f"Failed to save screenshot as {screenshot_path}")


def urlize(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9-_]', '', re.sub(r'\s', '_', text))


def get_config(env_name: str, default: str) -> str:
    cfg = os.getenv(env_name)
    if cfg is None or cfg == "":
        cfg = default
    return cfg
