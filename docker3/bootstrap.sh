#!/usr/bin/env bash

#Set the hostname
hostname docker3
echo "docker3" > /etc/hostname

#Clone Git repo containing config files
echo "###############################################################"
echo "Cloning https://github.com/ahunnargikar/vagrant_docker_registry........"
echo "###############################################################"
git clone https://github.com/ahunnargikar/vagrant_docker_registry
cd vagrant_docker_registry
git pull
cd ..

#Zookeeper
echo "3" > /etc/zookeeper/conf/myid

#Nginx config
sed -i 's/docker1/docker3/g' /etc/nginx/app-servers.include

#Elasticsearch config
sed -i 's/elasticsearch1/elasticsearch3/g' /etc/elasticsearch/elasticsearch.yml
sed -i 's/192.168.57.101/192.168.57.103/g' /etc/elasticsearch/elasticsearch.yml

echo "####################################"
echo "Rebooting........"
echo "####################################"
reboot