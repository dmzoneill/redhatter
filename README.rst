RedHat OTP VPN Auto Connect
===========================

USAGE OF THIS IS YOUR OWN PROBLEM

ONLY A PROOF OF CONCEPT, SHOULD NOT BE USED

Install::

    MacOS
 
        https://www.macports.org/install.php
        sudo port install oath-toolkit
        
    Linux 

        https://github.com/paolostivanin/OTPClient    
        expect

Configure::

    MacOS

        Go into viscosity preferences and click allow unsafe commands

        echo "<< secret >>" > hotp-secret
        echo "1" > hotp-counter
        # verify
        /opt/local/bin/oathtool -b -c $(cat ./hotp-counter) $(cat ./hotp-secret)

    Linux

        # your otpclient pw
        # this unlocks the otpclinet db
        echo "<<PW>>" > pw
        
        # this is the account name under 
        # otpclient-cli list
        echo "<<OAUTH.......>>" > oauth

        # your rh key
        echo "<<KEY>>" > key
        
        # connect uuid
        nmcli con show
        echo "<<connection uuid>>" >> uuid

Execute::

    ./vpn-connect

On Login::

    MacOS
        mkdir ~/Library/LaunchAgents/
        cp .config/com.rh.autoconnect.plist ~/Library/LaunchAgents/ 
        sed -i '' "s#daoneill#<<username>>#g"  ~/Library/LaunchAgents/com.rh.autoconnect.plist

    Linux
        cp -rv .config/autostart/*.desktop ~/.conf/autostart/

RedHat OTP Chrome Plugin
========================

Install::

    Google chrome
    pip3 install fastapi uvicorn

Configure::

    Go to extensions
    load unpacked
    point it at the rh-otp folder

Run::

    cd src_folder
    uvicorn main:app --reload

Run at boot::

    cp -rv .config/autostart/*.desktop ~/.conf/autostart/

Verify::

    curl -vv http://localhost:8000

Usage::

    In the extensions in the top right hand of the browser, pin the redhat icon.
    Hit the redhat button when on auth.redhat.com and it will fill in the password box

RedHat OSD console token fetcher
================================

Install::

    https://chromedriver.chromium.org/
    cp chromedriver /opt/chromedriver/chromedriver
    cp rhtoken /usr/local/bin/rhtoken
    chmod +x /usr/local/bin/rhtoken

Configure::

    Open the google chrome and add a new profile "SSO"
    Type "chrome:://version" in the location bar
    Note the profile path
    Modify rhtoken lines 27 & 30

Usage::
    
    rhtoken s # get a stage token    
    rhtoken p # get a production token    
    rhtoken e # get a ephemeral token
