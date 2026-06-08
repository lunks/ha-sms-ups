# SMS Legrand UPS — Home Assistant

Local monitoring and control of SMS Legrand Wi-Fi UPS devices.

## Install (HACS)

1. Add this repository as a custom repository (type: **Integration**).
2. Install **SMS Legrand UPS** and restart Home Assistant.
3. Add the integration — devices are auto-discovered on your network
   (or enter the host manually), then sign in.

## Entities

- **Sensors:** status, input/output voltage, battery level, output power, temperature, frequency
- **Binary sensors:** grid power, charging, on-battery, boost, bypass, overpower, battery test
- **Buttons:** battery test (quick / deep / stop)
- **Light:** RGB status LED (on supported models)

> Local polling over HTTPS using the device's self-signed certificate.
