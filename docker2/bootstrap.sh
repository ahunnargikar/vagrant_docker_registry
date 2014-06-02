#!/usr/bin/env bash

#Set the hostname
hostname docker2
echo "docker2" > /etc/hostname

#Clone Git repo containing config files
echo "###############################################################"
echo "Cloning https://github.com/ahunnargikar/vagrant-mesos........"
echo "###############################################################"
git clone https://github.com/ahunnargikar/vagrant_docker_registry
cd vagrant_docker_registry
git pull
cd ..

#Zookeeper
echo "2" > /etc/zookeeper/conf/myid

#Nginx config
sed -i 's/docker1/docker2/g' /etc/nginx/app-servers.include

#Elasticsearch config
sed -i 's/elasticsearch1/elasticsearch2/g' /etc/elasticsearch/elasticsearch.yml
sed -i 's/192.168.57.101/192.168.57.102/g' /etc/elasticsearch/elasticsearch.yml

#Disable services
update-rc.d -f marathon remove
echo "manual" >> /etc/init/marathon.conf

echo "####################################"
echo "Rebooting........"
echo "####################################"
reboot