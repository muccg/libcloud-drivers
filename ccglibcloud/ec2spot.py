# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Amazon EC2 Spot instance driver.
"""

import base64
from libcloud.utils.py3 import b, basestring
from libcloud.utils.xml import fixxpath, findtext, findall
from libcloud.compute.drivers.ec2 import EC2NodeDriver, NAMESPACE, RESOURCE_EXTRA_ATTRIBUTES_MAP


class SpotRequestState(object):
    """
    Standard states for a spot request

    :cvar OPEN: Spot request is open.
    :cvar CLOSED: Spot request is closed.
    :cvar FAILED: Spot request has failed.
    :cvar CANCELLED: Spot request is canceled.
    :cvar ACTIVE: Spot request is active.
    """
    OPEN = 0
    CLOSED = 1
    FAILED = 2
    CANCELLED = 3
    ACTIVE = 4


class EC2SpotRequest(object):
    """
    Class which stores information about an EC2 spot request.

    Note: This class is EC2 specific.
    """

    def __init__(self, id, instance_id, spot_price, state, status, message,
                 availability_zone_group, driver, extra=None):
        self.id = id
        self.instance_id = instance_id
        self.spot_price = spot_price
        self.state = state
        self.status = status
        self.message = message
        self.availability_zone_group = availability_zone_group
        self.driver = driver
        self.extra = extra

    def __repr__(self):
        return (('<EC2SpotRequest: id=%s>') % (self.id))


class EC2SpotNodeDriver(EC2NodeDriver):
    """
    Amazon EC2 driver with added support for spot instances.
    Ideally, these extra methods should make it into the main EC2NodeDrivers one day.

    http://docs.aws.amazon.com/AWSEC2/latest/APIReference/ApiReference-query-RequestSpotInstances.html
    """

    SPOT_REQUEST_STATE_MAP = {
        'open': SpotRequestState.OPEN,
        'closed': SpotRequestState.CLOSED,
        'failed': SpotRequestState.FAILED,
        'cancelled': SpotRequestState.CANCELLED,
        'active': SpotRequestState.ACTIVE
    }

    def ex_request_spot_instances(self, **kwargs):
        """
        Create a Spot Instance Request.

        Reference: http://bit.ly/8ZyPSy [docs.amazonwebservices.com]

        :keyword    spot_price: The spot price to bid. (required)
        :type       spot_price: ``str``
 
        :keyword    instance_count: The maximum number of Spot Instances to launch.
        :type       instance_count: ``int``

        :keyword    type: The Spot instance request type ("one-time" | "persistent").
        :type       type: ``str``

        :keyword    valid_from: The start date of the request.
        :type       valid_from: ``datetime.datetime`` 

        :keyword    valid_until: The end date of the request.
        :type       valid_until: ``datetime.datetime`` 

        :keyword    image: OS Image to boot on node. (required)
        :type       image: :class:`.NodeImage`

        :keyword    size: The size of resources allocated to this node. (required)
        :type       :class: `.NodeSize`

        :keyword    location: Which data center to create all your Spot instances in.
        :type       location: :class:`.NodeLocation`

        :keyword    keyname: The name of the key pair
        :type       keyname: ``str``

        :keyword    userdata: User data
        :type       userdata: ``str``

        :keyword    security_groups: A list of names of security groups to
                                        assign to the node.
        :type       security_groups:   ``list``

        :keyword    blockdevicemappings: ``list`` of ``dict`` block device
                    mappings.
        :type       blockdevicemappings: ``list`` of ``dict``

        :keyword    iamprofile: Name or ARN of IAM profile
        :type       iamprofile: ``str``

        :keyword    ebs_optimized: EBS-Optimized if True
        :type       ebs_optimized: ``bool``

        :keyword    subnet: The subnet to launch the instance into.
        :type       subnet: :class:`.EC2Subnet`
        """
        spot_price = kwargs["spot_price"]
        image = kwargs["image"]
        size = kwargs["size"]
        params = {
            'Action': 'RequestSpotInstances',
            'SpotPrice': str(spot_price),
            'LaunchSpecification.ImageId': image.id,
            'LaunchSpecification.InstanceType': size.id
        }

        if "instance_count" in kwargs:
            params["InstanceCount"] = str(kwargs["instance_count"])

        if "type" in kwargs:
            params["Type"] = kwargs["type"]

        if "valid_from" in kwargs:
            params["ValidFrom"] = kwargs["valid_from"].isoformat()

        if "valid_until" in kwargs:
            params["ValidUntil"] = kwargs["valid_until"].isoformat()

        if "location" in kwargs:
            availability_zone = getattr(kwargs["location"],
                                        "availability_zone", None)
            if availability_zone:
                if availability_zone.region_name != self.region_name:
                    raise AttributeError('Invalid availability zone: %s'
                                         % (availability_zone.name))
                params['LaunchSpecification.Placement.AvailabilityZone'] = availability_zone.name

        if 'keyname' in kwargs:
            params['LaunchSpecification.KeyName'] = kwargs['keyname']

        if 'userdata' in kwargs:
            userdata = base64.b64encode(b(kwargs['userdata'])).decode('utf-8')
            params['LaunchSpecification.UserData'] = userdata
 
        security_groups = kwargs.get('security_groups')
        if security_groups:
            if not isinstance(security_groups, (tuple, list)):
                security_groups = [security_groups]

            for sig in range(len(security_groups)):
                params['LaunchSpecification.SecurityGroup.%d' % (sig + 1,)] =\
                    security_groups[sig]

        if 'blockdevicemappings' in kwargs:
            params.update(self._get_block_device_mapping_params(
                          kwargs['blockdevicemappings']))

        iamprofile = kwargs.get('iamprofile')
        if iamprofile:
            if not isinstance(iamprofile, basestring):
                raise AttributeError('iamprofile not string')

            if iamprofile.startswith('arn:aws:iam:'):
                params['LaunchSpecification.IamInstanceProfile.Arn'] = iamprofile
            else:
                params['LaunchSpecification.IamInstanceProfile.Name'] = iamprofile

        if 'ebs_optimized' in kwargs:
            params['LaunchSpecification.EbsOptimized'] = kwargs['ebs_optimized']

        if 'subnet' in kwargs:
            params['LaunchSpecification.SubnetId'] = kwargs['subnet'].id

        print "Params is %s" % params
        object = self.connection.request(self.path, params=params).object
        spots = self._to_spot_requests(object, 'spotInstanceRequestSet/item')

        if len(spots) == 1:
            return spots[0]
        else:
            return spots

    def ex_cancel_spot_instance_request(self, spot_request):
        """
        Cancel the spot request by passing in the spot request object

        :param      spot_request: Spot request which should be used
        :type       spot_request: :class:`EC2SpotRequest`

        :rtype: ``bool``
        """
        params = {'Action': 'CancelSpotInstanceRequests'}
        params.update(self._pathlist('SpotInstanceRequestId', [spot_request.id]))
        res = self.connection.request(self.path, params=params).object
        state = findall(element=res,
                        xpath='spotInstanceRequestSet/item/state',
                        namespace=NAMESPACE)[0].text
        return self.SPOT_REQUEST_STATE_MAP[state] == SpotRequestState.CANCELLED

    def ex_list_spot_requests(self, spot_request_ids=None, filters=None):
        """
        List all spot requests

        spot_request_ids parameter is used to filter the list of
        spot requests that should be returned.

        :param      spot_request_ids: List of ``spot_request.id``
        :type       spot_request_ids: ``list`` of ``str``

        :param      filters: The filters so that the response includes
                             information for only certain spot requests.
        :type       filters: ``dict``

        :rtype: ``list`` of :class:`EC2SpotRequest`
        """

        params = {'Action': 'DescribeSpotInstanceRequests'}

        if spot_request_ids:
            params.update(self._pathlist('SpotInstanceRequestId', spot_request_ids))

        if filters:
            params.update(self._build_filters(filters))

        object = self.connection.request(self.path, params=params).object
        return self._to_spot_requests(object, 'spotInstanceRequestSet/item')

    def _to_spot_requests(self, object, xpath):
        return [self._to_spot_request(el)
                for el in object.findall(fixxpath(xpath=xpath,
                                                  namespace=NAMESPACE))]

    def _to_spot_request(self, element):
        try:
            instance_id = findtext(element=element, xpath='instanceId',
                                   namespace=NAMESPACE)
        except KeyError:
            instance_id = None

        spot_instance_request_id = findtext(element=element,
                                            xpath='spotInstanceRequestId',
                                            namespace=NAMESPACE)
        spot_price = findtext(element=element, xpath='spotPrice',
                              namespace=NAMESPACE)
        state = self.SPOT_REQUEST_STATE_MAP[findtext(element=element,
                                                     xpath="state",
                                                     namespace=NAMESPACE)]
        status = findtext(element=element, xpath="status/code",
                          namespace=NAMESPACE)
        message = findtext(element=element, xpath="status/message",
                           namespace=NAMESPACE)
        availability_zone_group = findtext(element=element,
                                           xpath="availabilityZoneGroup",
                                           namespace=NAMESPACE)
        launchSpecification = findall(element=element,
                                      xpath='launchSpecification',
                                      namespace=NAMESPACE)[0]

        # Get our extra dictionary
        extra = self._get_extra_dict(
            launchSpecification, RESOURCE_EXTRA_ATTRIBUTES_MAP['node'])

        # Add additional properties to our extra dictionary
        extra['block_device_mapping'] = self._to_device_mappings(launchSpecification)
        extra['groups'] = self._get_security_groups(launchSpecification)

        return EC2SpotRequest(id=spot_instance_request_id, instance_id=instance_id, spot_price=spot_price, state=state,
                              status=status, message=message, availability_zone_group=availability_zone_group,
                              driver=self.connection.driver, extra=extra)

    def _get_block_device_mapping_params(self, block_device_mapping):
        params = super(EC2SpotNodeDriver, self)._get_block_device_mapping_params(block_device_mapping=block_device_mapping)
        for key in params:
            params['LaunchSpecification.{0}'.format(key)] = params[key]
            del params[key]
        return params


class EC2EUSpotNodeDriver(EC2SpotNodeDriver):
    """
    Driver class for EC2 in the Western Europe Region.
    """
    name = 'Amazon EC2 (eu-west-1)'
    _region = 'eu-west-1'


class EC2USWestSpotNodeDriver(EC2SpotNodeDriver):
    """
    Driver class for EC2 in the Western US Region
    """
    name = 'Amazon EC2 (us-west-1)'
    _region = 'us-west-1'


class EC2USWestOregonSpotNodeDriver(EC2SpotNodeDriver):
    """
    Driver class for EC2 in the US West Oregon region.
    """
    name = 'Amazon EC2 (us-west-2)'
    _region = 'us-west-2'


class EC2APSESpotNodeDriver(EC2SpotNodeDriver):
    """
    Driver class for EC2 in the Southeast Asia Pacific Region.
    """
    name = 'Amazon EC2 (ap-southeast-1)'
    _region = 'ap-southeast-1'


class EC2APNESpotNodeDriver(EC2SpotNodeDriver):
    """
    Driver class for EC2 in the Northeast Asia Pacific Region.
    """
    name = 'Amazon EC2 (ap-northeast-1)'
    _region = 'ap-northeast-1'


class EC2SAEastSpotNodeDriver(EC2SpotNodeDriver):
    """
    Driver class for EC2 in the South America (Sao Paulo) Region.
    """
    name = 'Amazon EC2 (sa-east-1)'
    _region = 'sa-east-1'


class EC2APSESydneySpotNodeDriver(EC2SpotNodeDriver):
    """
    Driver class for EC2 in the Southeast Asia Pacific (Sydney) Region.
    """
    name = 'Amazon EC2 (ap-southeast-2)'
    _region = 'ap-southeast-2'
