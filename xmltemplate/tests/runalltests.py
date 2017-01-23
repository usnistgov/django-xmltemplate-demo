#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Run all of the unit tests for xmltemplate
"""
import unittest, sys, os.path

from xmltemplate.tests import test_models
from xmltemplate.tests import test_schema
from xmltemplate.tests import test_multi


if __name__ == '__main__':
    tr = unittest.TextTestRunner()
    for mod in [test_models, test_schema, test_multi]:
        print("{0}: ".format(mod.__name__))
        tr.run(mod.test_suite())
