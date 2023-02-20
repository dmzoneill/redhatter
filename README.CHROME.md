RedHat OTP Chrome Plugin
========================

Configure::

1. Go to extensions in your browser
2. click, load unpacked extension
3. point it at the rh-otp folder

Enable the companion service
============================

Run::

    cd src_folder
    uvicorn main:app --reload

Run at boot::

    # This is already described in the MacOSX/Linux readmes

Verify::

    curl -vv http://localhost:8000

Usage::

    In the extensions in the top right hand of the browser, pin the redhat icon.
    Hit the redhat button when on auth.redhat.com and it will fill in the password box
