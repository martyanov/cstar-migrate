#!/bin/sh

set -e

flake8 cstarmigrate
coverage erase
coverage run --source cstarmigrate -m py.test
coverage report --include='cstarmigrate/**' --omit='ctarmigrate/test/**'
