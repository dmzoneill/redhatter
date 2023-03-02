RedHat OTP VPN Auto Connect
===========================

Install::

    sudo (apt/dnf/..) install oathtool expect pass gpg

Configure::
    # setup your gpg if not already known

    $ gpg --list-secret-key
    /home/daoneill/.gnupg/pubring.kbx
    ---------------------------------
    sec   rsa3072 2022-08-01 [SC] [expires: 2024-07-31]
        0774BB9B2B5052B6244977F49FC1F6C979869721
    uid           [ultimate] David O Neill <dmz.oneill@gmail.com>
    ssb   rsa3072 2022-08-01 [E] [expires: 2024-07-31]


    # setup password store with that gpg key

    $ pass init 0774BB9B2B5052B6244977F49FC1F6C979869721
    mkdir: created directory '/home/daoneill/.password-store/'
    Password store initialized for 0774BB9B2B5052B6244977F49FC1F6C979869721

    $ pass insert redhat.com/hotp-secret
    $ pass insert redhat.com/associate-password

    $ pass show
    Password Store
    └── redhat.com
        ├── associate-password
        └── hotp-secret

    # Fall back is file, but this is not secure and shouldn't be used
    $ echo "<< secret >>" > hotp-secret

    # if you dont known how hotp works and what this number is
    # then create a new key on token.redhat.com, and start from 1
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
