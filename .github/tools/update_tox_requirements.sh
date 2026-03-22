#!/bin/bash

module_name="${@}"

cp ".paa/requirements_dev.txt" ".paa/requirements/requirements_tox.txt"
echo "" >> ".paa/requirements/requirements_tox.txt"
cat ".paa/requirements/requirements_$module_name.txt" >> ".paa/requirements/requirements_tox.txt"