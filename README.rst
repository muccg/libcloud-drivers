ccg-libcloud-drivers
====================

Working proof of concept of an EC2 driver for libcloud that uses spot instances rather than on demand. Created by gutting the existing libcloud EC2 driver and adding spot instance support, credit to original authors.

Licence
-------

Apache 2.0

Using
-----

To run as a developer::

    virtualenv-2.7 virt
    source virt/bin/activate
    pip install -e .
