#!/usr/bin/env bash

rm docker1.box
vagrant box remove docker1
vagrant up
vagrant package --base docker1 --output docker1.box
vagrant box add docker1 docker1.box
vagrant box list
vagrant up

cd docker2/
vagrant up
cd ..

cd docker3/
vagrant up