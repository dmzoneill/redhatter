RedHat OTP VPN Auto Connect
===========================

rh-otp-auto-connect is a tool to help Red Hat employees seamlessly connect to the company's virtual private network (VPN) using one-time passwords (OTP). The tool is designed to run on Red Hat Enterprise Linux (RHEL), Fedora or MacOSX systems, and it automatically retrieves and enters the OTP code needed for VPN authentication, streamlining the connection process.

The tool works by on staryup or by demand, and the tool will attempt to connect to the VPN using the user's saved credentials. If the connection requires an OTP code, the tool will automatically retrieve the code from the user's configured source (such as Google Authenticator or a hardware token) and enter it for the user.

rh-otp-auto-connect is especially useful for Red Hat employees who frequently need to connect to the company's VPN while working remotely or on-the-go. By automating the OTP entry process, the tool saves time and reduces the risk of human error when entering codes. The tool is open-source and available on GitHub, which means that it can be customized and adapted for use in other environments or by other organizations with similar VPN requirements.

Get started with:

- [Linux](https://github.com/dmzoneill/rh-otp-auto-connect/blob/main/README.LINUX.md)
- [MacOSX](https://github.com/dmzoneill/rh-otp-auto-connect/blob/main/README.MACOSX.md)

Install the companion chrome extension:

- [Chrome extension](https://github.com/dmzoneill/rh-otp-auto-connect/blob/main/README.CHROME.md)

![Browser shot](https://github.com/dmzoneill/rh-otp-auto-connect/blob/main/images/readme-image.png?raw=true)