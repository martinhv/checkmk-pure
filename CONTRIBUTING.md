# Contribution guide

## Manual test setup

Please run the following:

Please run:

```
docker compose build
docker compose up -d
```

Now the web interface should be available at `http://localhost:8080/monitoring/`. The username is `cmkadmin` and the
password is `test`.

## Running unit tests

Unit tests require the dependencies described in `requirements.txt` and Checkmk as a submodule. Please run:

```
git submodule init
git submodule update
pip install -r requirements.txt
cd tests
python -m unittest discover
```

## Running integration tests

The method is the same as running the unit tests above, but with the following environment variables exposed:

| Variable                 | Description                                                                                                                             | Default                                             |
|--------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------|
| `LIVE_FA_HOSTNAME`       | Hostname of a real FlashArray device.                                                                                                   | *empty*                                             |
| `LIVE_FA_APITOKEN`       | API token for a real FlashArray device.                                                                                                 | *empty*                                             |
| `LIVE_FA_CERT_FILE`      | Path to a certificate file for a real FlashArray device. Warning! If left empty, the live test will run without certificate validation. | *empty*                                             |
| `LIVE_FB_HOSTNAME`       | Hostname of a real FlashBlade device.                                                                                                   | *empty*                                             |
| `LIVE_FB_APITOKEN`       | API token for a real FlashBlade device.                                                                                                 | *empty*                                             |
| `LIVE_FB_CERT_FILE`      | Path to a certificate file for a real FlashBlade device. Warning! If left empty, the live test will run without certificate validation. | *empty*                                             |

## Running end-to-end tests

The end-to-end tests for this repository are implemented with [behave](https://behave.readthedocs.io/en/stable/)
and [Selenium](https://www.selenium.dev/). You will need an installed Firefox
and [geckodriver](https://github.com/mozilla/geckodriver) in order to run the tests. The default configuration works
automatically on Ubuntu 22.04 when Firefox is installed.

Here are the steps to run the tests:

1. Create a venv using `python -m venv venv`.
2. Activate the venv using `source venv/bin/activate`.
3. Install the test dependencies using `pip install -r requirements.txt`.
4. Enter the `tests` directory and run the behavior tests using `behave`.

### End-to-end test configuration

You can expose the following environment variables in order to change the test behavior:

| Variable                 | Description                                                                                                                             | Default                                             |
|--------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------|
| `CONTAINER_START`        | Automatically start the test container before each test scenario.                                                                       | `1`                                                 |
| `CONTAINER_STOP`         | Automatically stop the test container after each test scenario.                                                                         | `1`                                                 |
| `CONTAINER_UP_COMMAND`   | Command to start the test container with.                                                                                               | `docker compose up -d --wait checkmk`               |
| `CONTAINER_DOWN_COMMAND` | Command to stop the test container with.                                                                                                | `docker compose down -t 1`                          |
| `HTTP_ENDPOINT`          | The HTTP endpoint of the test container that should be called for tests.                                                                | `http://127.0.0.1:8080/`                            |
| `CHECKMK_SITE_NAME`      | Name of the Checkmk site in the container. This must match the container build parameters.                                              | `monitoring`                                        |
| `CHECKMK_SITE_USER`      | Username to use for the Checkmk login during tests. This must match the container build parameters.                                     | `cmkadmin`                                          |
| `CHECKMK_SITE_PASSWORD`  | Password to use for the Checkmk login during tests. This must match the container build parameters.                                     | `test`                                              |
| `GECKODRIVER_PATH`       | Path to the Geckodriver executable.                                                                                                     | `/snap/bin/geckodriver`                             |
| `HEADLESS`               | Set to 1 for headless mode, 0 to show the Firefox window during tests.                                                                  | `1` if the `DISPLAY` variable is set, `0` otherwise |
| `TEST_RUNNER_IP`         | IP address of the host running the tests. This is needed for simulating a FlashBlade/FlashArray instance                                | `192.168.199.1`                                     |
| `LIVE_FA_HOSTNAME`       | Hostname of a real FlashArray device.                                                                                                   | *empty*                                             |
| `LIVE_FA_APITOKEN`       | API token for a real FlashArray device.                                                                                                 | *empty*                                             |
| `LIVE_FA_CERT_FILE`      | Path to a certificate file for a real FlashArray device. Warning! If left empty, the live test will run without certificate validation. | *empty*                                             |
| `LIVE_FB_HOSTNAME`       | Hostname of a real FlashBlade device.                                                                                                   | *empty*                                             |
| `LIVE_FB_APITOKEN`       | API token for a real FlashBlade device.                                                                                                 | *empty*                                             |
| `LIVE_FB_CERT_FILE`      | Path to a certificate file for a real FlashBlade device. Warning! If left empty, the live test will run without certificate validation. | *empty*                                             |

### Running end-to-end tests via SSH

You can run the tests in headless mode on any server that has Docker and docker-compose available. However, if you want
to see the results of the test, you will need to enable X forwarding. To do this, you will need a local X server, such
as [XQuartz](https://www.xquartz.org/), [VcXsrv](https://sourceforge.net/projects/vcxsrv/)
or [WSLg](https://github.com/microsoft/wslg). You will need to run SSH with `ssh -X` to allow X forwarding.

Additionally, on Ubuntu 22.04 you will need to export the `XAUTHORITY` environment variable on the server for the
Snap-based Firefox to run properly:

```
export XAUTHORITY=~/.Xauthority
```

Please note, using `sudo su` will get rid of both the `XAUTHORITY` and the `DISPLAY` environment variables, both of
which are required to show the Firefox window. To work around this, we recommend adding your user to the `docker` group
to enable running tests as a non-root user. (Note, that this enables you to bypass sudo requirements for your user. Talk
to your security department before doing this on sensitive systems.)

## Packaging to an MKP file

We have created a tool to create an MKP package. Please run the following:

```
git submodule init
git submodule update
pip install -r requirements.txt
python tools/package.py
```

## Updating checkmk

If you want to update Checkmk to a later version, make sure to update both the Dockerfile and the Git submodule for code
completion.
