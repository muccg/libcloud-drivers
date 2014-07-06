import time
import os
from libcloud.compute.base import NodeImage
from libcloud.compute.providers import get_driver
from libcloud.compute.providers import set_driver
from ccglibcloud.ec2spot import SpotRequestState


SIZE_ID = 't1.micro'
AMI_ID = 'ami-f195f1cb'
KEYPAIR_NAME = 'ccg-syd-staging'
SECURITY_GROUP_NAMES = ['default', 'ssh']
NODE_NAME = 'test-node'
SPOT_PRICE = '0.08'
TAGS = {'Name': NODE_NAME}
TERMINATED_TAGS = {'Name': 'terminated_{0}'.format(NODE_NAME)}


def create_spot_request(accessid, secretkey):

    # load our third party driver
    set_driver('ec2spot',
               'ccglibcloud.ec2spot',
               'EC2APSESydneySpotNodeDriver')
    cls = get_driver('ec2spot')
    driver = cls(accessid, secretkey)

    sizes = driver.list_sizes()
    size = [s for s in sizes if s.id == SIZE_ID][0]
    image = NodeImage(id=AMI_ID, name=None, driver=driver)

    # create the spot instance
    spot = driver.create_node(name=NODE_NAME, image=image, size=size,
                              ex_spot_price=SPOT_PRICE,
                              ex_keyname=KEYPAIR_NAME,
                              ex_securitygroup=SECURITY_GROUP_NAMES)

    # wait for the spot request to be fullfilled
    while spot.state == SpotRequestState.OPEN:
        print spot.message
        time.sleep(5)
        spot = driver.ex_list_spot_requests(spot_request_ids=[spot.id])[0]

    # clean up after ourselves if the request was fullfilled
    if spot.state == SpotRequestState.ACTIVE:
        print spot.message
        print spot.instance_id

        # tag the node
        node = driver.list_nodes(ex_node_ids=[spot.instance_id])[0]
        print driver.ex_create_tags(node, TAGS)

        # cancel the spot request
        print driver.ex_cancel_spot_instance_request(spot)

        # destroy the node and update the tags
        print driver.destroy_node(node)
        print driver.ex_create_tags(node, TERMINATED_TAGS)

        # check the spot request is cancelled
        spot = driver.ex_list_spot_requests(spot_request_ids=[spot.id])[0]
        assert(spot.state == SpotRequestState.CANCELLED)


def main():
    accessid = os.getenv('ACCESSID')
    secretkey = os.getenv('SECRETKEY')

    if accessid and secretkey:
        create_spot_request(accessid, secretkey)
    else:
        print 'ACCESSID and SECRETKEY are sourced from the environment'

if __name__ == "__main__":
    main()
