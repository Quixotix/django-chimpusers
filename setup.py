from distutils.core import setup
import os
import chimpusers

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='django-chimpusers', 
    version=chimpusers.get_version(),
    description='Integrate Django users with a MailChimp mailing list.',
    long_description=read('README.markdown'),
    author='Micah Carrick',
    author_email='micah@quixotix.com',
    url='git@github.com:Quixotix/django-chimpusers.git',
    packages=['chimpusers'],
    license='BSD',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: BSD License",
    ],
)
