from setuptools import setup

setup(
    name='ccg-libcloud-drivers',
    version='0.0.1',
    author='CCG',
    author_email='contact@ccg.murdoch.edu.au',
    url='http://ccg.murdoch.edu.au/',
    license='Apache 2.0',
    description='CCG libcloud drivers',

    packages=['ccglibcloud'],

    install_requires=[
        "apache-libcloud==0.15.1",
    ],
)
