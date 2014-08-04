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

To load the driver from your Python code::

    from libcloud.compute.providers import get_driver
    from ccglibcloud.ec2spot import set_spot_drivers

    set_spot_drivers()
    cls = get_driver('ec2spot')
    driver = cls(ACCESS_ID, SECRET_KEY)

Run the example, its CCG specific and loads AWS creds from your environment::

    python example.py

.. _libcloud: https://libcloud.apache.org/
.. _spot: http://docs.aws.amazon.com/AWSEC2/latest/APIReference/ApiReference-query-RequestSpotInstances.html
