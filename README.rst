ccg-libcloud-drivers
====================

Working proof of concept of an EC2 driver for libcloud_ that uses spot_ instances rather than on demand. Created by gutting the existing libcloud EC2 driver and adding spot instance support, credit to original authors.

Licence
-------

Apache 2.0

Using
-----

To install as a developer::

    virtualenv-2.7 virt
    source virt/bin/activate
    pip install -e .

To load the driver::

    from libcloud.compute.providers import get_driver
    from libcloud.compute.providers import set_driver

    set_driver('ec2spot',
               'ccglibcloud.ec2spot',
               'EC2APSESydneySpotNodeDriver')
    cls = get_driver('ec2spot')
    driver = cls(ACCESS_ID, SECRET_KEY)

.. _libcloud: https://libcloud.apache.org/
.. _spot: http://docs.aws.amazon.com/AWSEC2/latest/APIReference/ApiReference-query-RequestSpotInstances.html
