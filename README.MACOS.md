RedHat OTP VPN Auto Connect
===========================

USAGE OF THIS IS YOUR OWN PROBLEM

ONLY A PROOF OF CONCEPT, SHOULD NOT BE USED

Install::

    https://www.macports.org/install.php
    sudo port install oath-toolkit


Configure::

    echo "<< secret >>" > hotp-secret
    echo "1" > hotp-counter
    
    # verify oathtool is the $PATH

    oathtool -b -c $(cat ./hotp-counter) $(cat ./hotp-secret)

    Go into viscosity preferences and click allow unsafe commands

Execute::

    ./vpn-connect

On Login::

    mkdir ~/Library/LaunchAgents/
    cp .config/*.plist ~/Library/LaunchAgents/ 
