#!/usr/bin/env bash

cd docker3/
vagrant destroy --force
cd ..

cd docker2/
vagrant destroy --force
cd ..

vagrant destroy --force