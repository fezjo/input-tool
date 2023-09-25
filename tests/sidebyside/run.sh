#!/bin/bash

input-generator idf -g cat
input-tester -FD sol-a.py sol-b.py
