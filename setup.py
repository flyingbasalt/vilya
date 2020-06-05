#!/usr/bin/env python

from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='vilya',
    version='0.1.0.dev10',
    author='Flying Stone',
    #author_email='flying.basalt@gmail.com',
    description='Monitoring for Elrond Network nodes',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/flyingbasalt/vilya',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        'Operating System :: POSIX',
    ],
    packages=['vilya'],
    #package_dir={'vilya': 'src/vilya'},
    entry_points={
        'console_scripts': [
            'vilya=vilya.vilya:main',
            ],
        }, 
    #package_data={'mypkg': ['data/*.dat']},
    data_files=[('vilya', ['vilya/config.toml'])],
    python_requires='>=3.6',
    install_requires=['psutil', 'tomlkit'],
)

