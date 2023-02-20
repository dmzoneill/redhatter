RedHat OTP VPN Auto Connect
===========================

USAGE OF THIS IS YOUR OWN PROBLEM

ONLY A PROOF OF CONCEPT, SHOULD NOT BE USED

Install::

    sudo (apt/dnf/..) install oathtool expect        

Configure::

    echo "<< secret >>" > hotp-secret
    echo "1" > hotp-counter
    
    # verify oathtool is the $PATH

    oathtool -b -c $(cat ./hotp-counter) $(cat ./hotp-secret)

    # connect uuid
    nmcli con show
    echo "<<connection uuid>>" >> uuid

Execute::

    ./vpn-connect

On Login::

    cp -rv .config/autostart/*.desktop ~/.conf/autostart/
