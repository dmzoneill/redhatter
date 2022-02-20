RedHat OTP VPN Auto Connect
===========================

USAGE OF THIS IS YOUR OWN PROBLEM

ONLY A PROOF OF CONCEPT, SHOULD NOT BE USED

Install::

    MacOS
 
        https://www.macports.org/install.php
        sudo port install oath-toolkit
        
    Linux 

        sudo (apt/dnf/..) install oathtool expect        

Configure::

    echo "<< secret >>" > hotp-secret
    echo "1" > hotp-counter
    
    # verify oathtool is the $PATH

    oathtool -b -c $(cat ./hotp-counter) $(cat ./hotp-secret)

    MacOS

        Go into viscosity preferences and click allow unsafe commands

    Linux
        
        # connect uuid
        nmcli con show
        echo "<<connection uuid>>" >> uuid

Execute::

    ./vpn-connect

On Login::

    MacOS

        mkdir ~/Library/LaunchAgents/
        cp .config/*.plist ~/Library/LaunchAgents/ 
        
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

    Linux
    
        cp -rv .config/autostart/*.desktop ~/.conf/autostart/
    
    MacOS
    
        cp .config/*.plist ~/Library/LaunchAgents/

Verify::

    curl -vv http://localhost:8000

Usage::

    In the extensions in the top right hand of the browser, pin the redhat icon.
    Hit the redhat button when on auth.redhat.com and it will fill in the password box