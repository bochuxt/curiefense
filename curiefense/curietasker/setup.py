#!/usr/bin/env python

from distutils.core import setup

setup(name='curietasker',
      version='0.6',
      description='Curiefense task scheduler',
      author='Reblaze',
      author_email='phil@reblaze.com',
      packages=['curietasker'],
      scripts=['bin/curietasker'],
      install_requires=[
#          "curieconf",
      ],
)
