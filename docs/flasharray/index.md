---
hide:
  - navigation
  - toc
---

# FlashArray Checkmk Configuration Guide

## Setting up a host

In order to use the FlashArray monitoring, first you need to set up a host. Please head to `Setup` &rarr; `Hosts` and
add a host. The form should be filled out as follows:

- `Hostname` **(required)**: Enter the hostname you want the FlashArray to show up as. If you don't intend to provide an
  IP address,
  this hostname should be resolvable via DNS.
- `IP address family`: if your FlashArray is reachable over IPv6, check the checkbox and change the setting
  to `IPv6 only` or `IPv4/IPv6 dual-stack`.
- `IPv4 address`: If your FlashArray hostname is not resolvable via DNS, check the checkbox and enter the IPv4 address
  of the FlashArray.
- `IPv6 address`: If your FlashArray hostname is not resolvable via DNS, check the checkbox and enter the IPv6 address
  of the FlashArray.
- `Checkmk agent / API integrations` **(required)**: Check the checkbox and change this setting
  to `Configured API integrations, no Checkmk agent`.

Now click `Save & run service discovery`.

## Setting up the API integration

Head to `Setup` &rarr; `Other integrations` and select `Pure Storage FlashArray`.

<figure markdown>
![Location of the FlashArray integration](flasharray-location.png)
</figure>

Now click the `Add rule` button and fill out the following fields:

- `API token` **(required)**: Enter your FlashArray API token here.
- `TLS certificate verification` **(strongly recommended)**: This checkbox enables verifying that the connection is secure. *Disabling this may enable an attacker to capture your API keys.*
- `TLS certificate` **(required if verification is enabled)**: Paste the certificate of your FlashBlade if the TLS certificate verification is enabled. (See the hint below.)
- `Explicit hosts`: Limit this rule to the host you just created.

- ??? tip "Obtaining the certificate"
    Open the FlashArray web interface and click the address bar of your browser. Select the certificate option.
    
    <figure markdown>
    ![](cert-step1.png)
    </figure>
    
    Select the `Details` tab and click `Export...`.
     
    <figure markdown>
    ![](cert-step2.png)
    </figure>

    Finally, open the downloaded file in a text editor and copy the contents.

!!! warning "Do not disable TLS certificate verification for production setups!"
    TLS certificate verification ensures that the connection between Checkmk and the FlashArray is secure. Without it, an attacker can intercept the connection and obtain the API token for the device.

<figure markdown>
![Configuration interface of the FlashArray integration](flasharray-configuration.png)
</figure>

## Advanced configuration

You can configure additional options by clicking the `show more ...` button on the `PureStorage FlashArray` box. It opens up the following options:

| Option                                                    | Default   | Description                                                                                                                                |
|-----------------------------------------------------------|-----------|--------------------------------------------------------------------------------------------------------------------------------------------|
| Port                                                      | `443`     | Port number to reach the FlashArray on. Do not change this option unless you need the check to go through a reverse.                       |
| Array checks / Custom warning threshold                   | `80%`     | Sets the level at which the array checks (space usage) will switch to `WARN`.                                                              |
| Array checks / Custom critical threshold                  | `90%`     | Sets the level at which the array checks (space usage) will switch to `CRIT`.                                                              |
| Certificate expiration checks / Custom warning threshold  | `90 days` | If the certificate expires in fewer than the specified number of days, the certificate check will switch to `WARN`                         |
| Certificate expiration checks / Custom critical threshold | `30 days` | If the certificate expires in fewer than the specified number of days, the certificate check will switch to `CRIT`                         |
| Hardware service name customization | N/A       | Here, you can customize how hardware services are reported. Specify the hardware type in the API to add a prefix and a suffix to the name. |
| Report alerts as temporary services                       | `off`     | If enabled, alerts from the FlashArray will be translated to temporary services. See [Alerts reporting](../alerts/index.md) for details.   |
