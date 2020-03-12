#!/bin/env python
# encoding: utf-8

from __future__ import unicode_literals

from yaml import Loader, SafeLoader
from cstarmigrate.cli import main


# Force YAML to load strings as unicode
def construct_yaml_str(self, node):
    # Override the default string handling function
    # to always return unicode objects
    return self.construct_scalar(node)


Loader.add_constructor('tag:yaml.org,2002:str', construct_yaml_str)
SafeLoader.add_constructor('tag:yaml.org,2002:str', construct_yaml_str)


if __name__ == '__main__':
    main()
