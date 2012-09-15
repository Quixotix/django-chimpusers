import chimpusers
import distribute_setup
distribute_setup.use_setuptools()

import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='django-chimpusers', 
    version=chimpusers.get_version(),
    description='Integrate Django users with a MailChimp mailing list.',
    long_description=read('README.md'),
    author='Micah Carrick',
    author_email='micah@quixotix.com',
    url='https://github.com/Quixotix/django-chimpusers',
    packages=['chimpusers', 'chimpusers.management', 'chimpusers.management.commands'],
    license='BSD',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: BSD License",
    ],
)
