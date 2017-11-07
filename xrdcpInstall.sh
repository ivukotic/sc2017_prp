wget http://storage-ci.web.cern.ch/storage-ci/debian/xrootd/pool/artful/master/x/xrootd/xrootd-client_20171105-c4b77813_amd64.deb
wget http://storage-ci.web.cern.ch/storage-ci/debian/xrootd/pool/artful/master/x/xrootd/xrootd-client-libs_20171105-c4b77813_amd64.deb
wget http://storage-ci.web.cern.ch/storage-ci/debian/xrootd/pool/artful/master/x/xrootd/xrootd-libs_20171105-c4b77813_amd64.deb
wget http://ftp.us.debian.org/debian/pool/main/r/readline/libreadline7_7.0-3_amd64.deb
apt install ./libreadline7_7.0-3_amd64.deb
apt install ./xrootd-libs_20171105-c4b77813_amd64.deb
apt install ./xrootd-client-libs_20171105-c4b77813_amd64.deb
apt install ./xrootd-client_20171105-c4b77813_amd64.deb 

