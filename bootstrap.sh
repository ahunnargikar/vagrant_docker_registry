#!/usr/bin/env bash

apt-get update

MESOS_VERSION=0.18.2
PROTOBUF_VERSION=2.5.0

#Set the hostname
hostname docker1
echo "docker1" > /etc/hostname
echo "192.168.57.101    zookeeper1 nginx1 docker1 registry1 elasticsearch1 mesos1 marathon1" >> /etc/hosts
echo "192.168.57.102    zookeeper2 nginx2 docker2 registry2 elasticsearch2 mesos2 marathon1" >> /etc/hosts
echo "192.168.57.103    zookeeper3 nginx3 docker3 registry3 elasticsearch3 mesos3 marathon1" >> /etc/hosts

#Install base packages
echo "####################################"
echo "Installing base packages........"
echo "####################################"
apt-get -y install g++ python-dev zlib1g-dev libssl-dev libcurl4-openssl-dev libsasl2-modules python-setuptools libsasl2-dev make daemon
apt-get -y install build-essential python-dev libevent-dev python-pip libssl-dev liblzma-dev libffi-dev redis-server python-novaclient
apt-get -y install curl wget git-core mlocate tree unzip 

#Install Java & Maven
echo "####################################"
echo "Installing JDK7 & Maven........"
echo "####################################"
apt-get -y install default-jdk maven
java -version

#Clone Git repo containing config files
echo "#######################################################################"
echo "Cloning https://github.com/ahunnargikar/vagrant_docker_registry........"
echo "#######################################################################"
git clone https://github.com/ahunnargikar/vagrant_docker_registry

#Install Zookeeper
echo "####################################"
echo "Installing Zookeeper........"
echo "####################################"
apt-get -y install zookeeperd
echo "1" > /etc/zookeeper/conf/myid
cp vagrant_docker_registry/zookeeper/zoo.cfg /etc/zookeeper/conf/zoo.cfg

#Install Mesos
echo "####################################"
echo "Installing Mesos........"
echo "####################################"
cp -rf vagrant_docker_registry/mesos/mesos-master /etc/mesos-master
cp -rf vagrant_docker_registry/mesos/mesos-slave /etc/mesos-slave
wget http://downloads.mesosphere.io/master/ubuntu/13.10/mesos_${MESOS_VERSION}_amd64.deb
wget http://downloads.mesosphere.io/master/ubuntu/13.10/mesos-${MESOS_VERSION}-py2.7-linux-x86_64.egg
dpkg -i mesos_${MESOS_VERSION}_amd64.deb
easy_install mesos-${MESOS_VERSION}-py2.7-linux-x86_64.egg
sed -i '/--recover=cleanup/d' /usr/bin/mesos-init-wrapper
cp vagrant_docker_registry/mesos/mesos/zk /etc/mesos/zk

#Install protobuf
echo "###############################################"
echo "Installing Protobuf ${PROTOBUF_VERSION}......."
echo "###############################################"
wget https://protobuf.googlecode.com/files/protobuf-${PROTOBUF_VERSION}.tar.gz
tar -xzvf protobuf-${PROTOBUF_VERSION}.tar.gz; cd protobuf-${PROTOBUF_VERSION}/
./configure
make
#make check
make install
ldconfig
protoc --version
cd ..

#Install Marathon Framework
echo "####################################"
echo "Installing Marathon Framework......."
echo "####################################"
#git clone https://github.com/mesosphere/marathon
#cd marathon
#sed -i 's#\(<mesos.version>\).*\(</mesos.version>\)#\1'${MESOS_VERSION}'\2#g' pom.xml
#sed -i 's#\(<protobuf.version>\).*\(</protobuf.version>\)#\1'${PROTOBUF_VERSION}'\2#g' pom.xml
#protoc --java_out=src/main/java/ --proto_path=/usr/local/include/mesos/ --proto_path=src/main/proto/ src/main/proto/marathon.proto
#git status
#mvn package
#cd ..
curl -O http://downloads.mesosphere.io/marathon/marathon-0.5.1/marathon-0.5.1.tgz
tar xzf marathon-0.5.1.tgz
mv marathon-0.5.1 /usr/local/marathon
mkdir -p /etc/marathon
cp vagrant-mesos/marathon/marathon.conf /etc/marathon/marathon.conf
cp vagrant-mesos/marathon/marathon.init /etc/init/marathon.conf

#Install Docker
echo "####################################"
echo "Installing Docker........"
echo "####################################"
echo deb http://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list
apt-get -y update
apt-get -y --force-yes install lxc-docker
service docker restart

#Installing backend search modules
echo "##########################################"
echo "Installing registry search modules........"
echo "##########################################"
cp -rf vagrant_docker_registry/modules/elasticsearchindex /usr/local/lib/python2.7/dist-packages/elasticsearchindex
#cp -rf vagrant_docker_registry/modules/solrindex /usr/local/lib/python2.7/dist-packages/solrindex

#Install Docker registry
echo "####################################"
echo "Installing Docker registry........"
echo "####################################"
git clone https://github.com/dotcloud/docker-registry.git
mv docker-registry /usr/local/docker-registry
cp vagrant_docker_registry/docker_registry/config.yml /usr/local/docker-registry/config/config.yml
pushd /usr/local/docker-registry
pip install .
mkdir /var/log/docker-registry
popd
cp vagrant_docker_registry/docker_registry/docker-registry.conf /etc/init/docker-registry.conf
service docker-registry restart

#Install Pyelasticsearch
echo "####################################"
echo "Installing Pyelasticsearch........"
echo "####################################"
pip install pyelasticsearch

#Install Elasticsearch
echo "####################################"
echo "Installing Elasticsearch........"
echo "####################################"
wget -O - http://packages.elasticsearch.org/GPG-KEY-elasticsearch | apt-key add -
echo deb http://packages.elasticsearch.org/elasticsearch/1.2/debian stable main > /etc/apt/sources.list.d/elasticsearch.list
apt-get update
apt-get install elasticsearch
update-rc.d elasticsearch defaults 95 10
cp vagrant_docker_registry/elasticsearch/elasticsearch.yml /etc/elasticsearch/elasticsearch.yml
/etc/init.d/elasticsearch restart
/usr/share/elasticsearch/bin/plugin -install mobz/elasticsearch-head

# #Install Zookeeper
# echo "####################################"
# echo "Installing Zookeeper........"
# echo "####################################"
# apt-get -y install zookeeperd
# echo "1" > /etc/zookeeper/conf/myid
# cp vagrant_docker_registry/zookeeper/zoo.cfg /etc/zookeeper/conf/zoo.cfg
# 
# #Install Solr
# echo "####################################"
# echo "Installing Solr........"
# echo "####################################"
# apt-get install -y tomcat7 tomcat7-docs tomcat7-admin
# cp vagrant_docker_registry/solr/tomcat-users.xml /etc/tomcat7/tomcat-users.xml
# wget http://www.gtlib.gatech.edu/pub/apache/lucene/solr/4.8.1/solr-4.8.1.zip
# unzip solr-4.8.1.zip
# mv solr-4.8.1 /usr/local/solr
# cp /usr/local/solr/example/lib/ext/* /usr/share/tomcat7/lib/
# cp /usr/local/solr/dist/solr-4.8.1.war /var/lib/tomcat7/webapps/solr.war
# cp -R /usr/local/solr/example/solr /var/lib/tomcat7/
# chown -R tomcat7:tomcat7 /var/lib/tomcat7/solr
# 
# cp -rf vagrant_docker_registry/solr/docker_registry /var/lib/tomcat7/solr/docker_registry
# chown -R tomcat7:tomcat7 /var/lib/tomcat7/solr/docker_registry
# service tomcat7 restart

#Install & configure Nginx
echo "####################################"
echo "Installing Nginx........"
echo "####################################"
apt-get -y install nginx
cp vagrant_docker_registry/nginx/app-servers.include /etc/nginx/app-servers.include
cp vagrant_docker_registry/nginx/nginx.conf /etc/nginx/nginx.conf
rm -rf /etc/nginx/sites-available
cp -rf vagrant_docker_registry/nginx/sites-available /etc/nginx/sites-available/
update-rc.d nginx defaults
/etc/init.d/nginx restart

# echo "####################################"
# echo "Rebooting........"
# echo "####################################"
#reboot