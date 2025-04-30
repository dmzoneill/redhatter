RedHat OTP VPN Auto Connect
===========================

## Install
```
$ sudo (apt/dnf/..) install oathtool expect pass gpg
```

## Configure
    
Setup your gpg if not already known
```
$ gpg --list-secret-key
/home/daoneill/.gnupg/pubring.kbx
---------------------------------
sec   rsa3072 2022-08-01 [SC] [expires: 2024-07-31]
    0774BB9B2B5052B6244977F49FC1F6C979869721
uid           [ultimate] David O Neill <dmz.oneill@gmail.com>
ssb   rsa3072 2022-08-01 [E] [expires: 2024-07-31]
```

Setup password store with that gpg key
```
$ pass init 0774BB9B2B5052B6244977F49FC1F6C979869721
mkdir: created directory '/home/daoneill/.password-store/'
Password store initialized for 0774BB9B2B5052B6244977F49FC1F6C979869721
```

Insert secrets, (associate password and OTP secret)
```
$ pass insert redhat.com/hotp-secret
$ pass insert redhat.com/hotp-counter
$ pass insert redhat.com/associate-password
$ pass insert redhat.com/username
$ pass insert redhat.com/nm-uuid

$ pass show
Password Store
└── redhat.com
    ├── associate-password
    └── hotp-counter
    └── hotp-secret
    └── username
    └── nm-uuid
```

Execute
```
$ ./vpn-connect
```

On Login
```
$ cp -rv .config/autostart/*.desktop ~/.conf/autostart/
```

System service
```
$ mkdir -p ~/.config/systemd/user
$ cp -rvf .config/systemd/user/* ~/.config/systemd/user/
$ systemctl --user daemon-reload
$ systemctl --user enable rhotp
$ systemctl --user start rhotp

```
