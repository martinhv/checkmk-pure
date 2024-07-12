from typing import Optional

from behave import runner
from selenium.webdriver.firefox import webdriver

from purestorage_checkmk_test.flasharray.mock import FlashArray
from purestorage_checkmk_test.flasharray.mock_array import ArrayContainer
from purestorage_checkmk_test.flasharray.mock_certificates import CertificatesContainer
from purestorage_checkmk_test.flasharray.mock_controllers import ControllersContainer
from purestorage_checkmk_test.flasharray.mock_drives import DrivesContainer
from purestorage_checkmk_test.flasharray.mock_hardware import HardwaresContainer
from purestorage_checkmk_test.flashblade.mock import FlashBlade
from purestorage_checkmk_test.flashblade.mock_blades import BladesContainer
from purestorage_checkmk_test.flashblade.mock_hardware import HardwareContainer


class BrowserContext(runner.Context):
    browser: webdriver.WebDriver

    flashblade: Optional[FlashBlade]
    flashblade_blades: Optional[BladesContainer]
    flashblade_hardware: Optional[HardwareContainer]

    flasharray: Optional[FlashArray]
    flasharray_drives: Optional[DrivesContainer]
    flasharray_controllers: Optional[ControllersContainer]
    flasharray_hardwares: Optional[HardwaresContainer]
    flasharray_arrays: Optional[ArrayContainer]
    flasharray_certificates: Optional[CertificatesContainer]
