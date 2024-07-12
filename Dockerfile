# This file builds a minimalistic CentOS Stream based container image for use as a testing platform for CheckMK plugins.
# This is NOT intended to be a production-grade Checkmk setup!
#
# Design considerations:
#
# - Base image: we chose CentOS Stream because it is closest to the Enterprise RHEL that is available without a
#   commercial subscription.
# - GPG signing/checksums: We opted for checksums to validate packages because it is simpler and updating the Checkmk
#   version requires updating configuration options anyway.
# - init.py: Checkmk Dockerfile seems to use the crond as a canary for the container to die. However, we want to
#   actually monitor the OMD processes. Since they use legacy init scripts, the only way to do that is to regularly
#   query "omd status". This is done by init.py, which serves as the init process of the container image.
# - The file is subdivided into the dev and prod stage. The dev stage is meant for when you want to mount the files into
#   the container. The prod stage is meant for when you want to install an mkp file for testing.

# CENTOS_VERSION specifies both the version for the CentOS Stream image and the Checkmk download.
ARG CENTOS_VERSION=9
# BASE_IMAGE is the base container image. Keep in mind that the code has only been tested with the official CentOS
# Stream 8 image from Quay.
ARG BASE_IMAGE=quay.io/centos/centos:stream${CENTOS_VERSION}
# CHECKMK_VERSION specifies the exact Checkmk version to download. This must correspond to the hash below.
ARG CHECKMK_VERSION=2.2.0p27
# CHECKMK_HASH is the SHA-256 hash to validate the downloaded RPM against.
ARG CHECKMK_HASH="8b3a04205551c54d809c3c7823b9145cd97fb47643735a9c3ebe7219552d610e"
# CHECKMK_URL is the address from which to download Checkmk.
ARG CHECKMK_URL=https://download.checkmk.com/checkmk/${CHECKMK_VERSION}/check-mk-raw-${CHECKMK_VERSION}-el${CENTOS_VERSION}-38.x86_64.rpm
# CHECKMK_SITE_NAME provides the name for the initial Checkmk site.
ARG CHECKMK_SITE_NAME=monitoring
# CHECKMK_SITE_PASSWORD provides the initial admin password for the Checkmk site.
ARG CHECKMK_SITE_PASSWORD=test
# PYDEVD_PYCHARM_VERSION is the version of the pydevd-pycharm version to install for debugging.
ARG PYDEVD_PYCHARM_VERSION=231.8770.66

FROM ${BASE_IMAGE} AS dev

ARG RHEL_VERSION
ARG CHECKMK_VERSION
ARG CHECKMK_HASH
ARG CHECKMK_URL
ARG CHECKMK_SITE_NAME
ARG CHECKMK_SITE_PASSWORD
ARG PYDEVD_PYCHARM_VERSION

RUN echo -e "\033[0;32mPerforming base setup...\033[0m" && \
    dnf install -y dnf-plugins-core procps-ng python3.11 && \
    dnf config-manager --enable crb && \
    dnf clean all
RUN echo -e "\033[0;32mDownloading and installing Checkmk from ${CHECKMK_URL}...\033[0m" && \
    curl -o /tmp/checkmk.rpm "${CHECKMK_URL}" && \
    PACKAGE_HASH=$(sha256sum /tmp/checkmk.rpm | cut -d ' ' -f 1) && \
    test "${PACKAGE_HASH}" = "${CHECKMK_HASH}" && \
    dnf install -y /tmp/checkmk.rpm && \
    rm /tmp/checkmk.rpm && \
    dnf clean all
RUN echo -e "\033[0;32mCreating Checkmk site...\033[0m" && \
    omd create -u 1000 -g 1000 --admin-password "${CHECKMK_SITE_PASSWORD}" --no-tmpfs "${CHECKMK_SITE_NAME}" && \
    omd config "${CHECKMK_SITE_NAME}" set APACHE_TCP_ADDR 0.0.0.0 && \
    omd config "${CHECKMK_SITE_NAME}" set APACHE_TCP_PORT 8080 && \
    sed -i -e 's/UseCanonicalName On/UseCanonicalName Off/' "/omd/sites/${CHECKMK_SITE_NAME}/etc/apache/apache.conf"
RUN echo -e "\033[0;32mInstalling dev tools...\033[0m" && \
    "/omd/sites/${CHECKMK_SITE_NAME}/bin/python3.11" -m pip install "pydevd_pycharm~=${PYDEVD_PYCHARM_VERSION}"
RUN echo -e "\033[0;32mInstalling mkp...\033[0m" && \
    "/omd/sites/${CHECKMK_SITE_NAME}/bin/python3.11" -m pip install "mkp"
RUN echo -e "\033[0;32mInstalling py-pure-client...\033[0m" && \
    "/omd/sites/${CHECKMK_SITE_NAME}/bin/python3.11" -m pip install "py-pure-client"

RUN echo -e "\033[0;32mSetting up entrypoint...\033[0m"
COPY --chmod=0755 --chown=root:root rootfs/init.py /
ENTRYPOINT ["/init.py"]
CMD []
HEALTHCHECK --interval=5s --timeout=5s --start-period=60s CMD omd status || exit 1

EXPOSE 8080

# The prod target is meant for an mkp-based installation.
FROM scratch AS prod
COPY --from=dev / /
COPY build/purestorage.mkp /
WORKDIR /omd/sites/monitoring
USER monitoring
ENV PATH=/omd/sites/monitoring/lib/perl5/bin:/omd/sites/monitoring/local/bin:/omd/sites/monitoring/bin:/omd/sites/monitoring/local/lib/perl5/bin:/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/omd/sites/monitoring/var/checkmk/packages
RUN mkp add /purestorage.mkp
RUN mkp enable purestorage
USER root
ENTRYPOINT ["/init.py"]
CMD []
HEALTHCHECK --interval=5s --timeout=5s --start-period=60s CMD omd status || exit 1

ONBUILD RUN echo -e "\033[0;31mThis image is not meant as a base image. Please build your own.\033[0m" && exit 1
