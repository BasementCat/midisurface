import os

from setuptools import setup

# Using vbox, hard links do not work
if os.environ.get('USER','') == 'vagrant':
    del os.link

with open('README.md', 'r') as fp:
    longdesc = fp.read()

setup(
    name='midisurface',
    version='0.1.0',
    description='Use MIDI control surfaces with Python',
    long_description=longdesc,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: Other/Proprietary License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
    ],
    url='https://github.com/BasementCat/midisurface',
    author='Alec Elton',
    author_email='alec.elton@gmail.com',
    license='MIT',
    packages=['midisurface'],
    install_requires=['mido', 'python-rtmidi'],
    # test_suite='nose.collector',
    # tests_require=['nose'],
    zip_safe=False
)