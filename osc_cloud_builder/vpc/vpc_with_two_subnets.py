#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Create a VPC with 2 subnets and a nat instance
    - First subnet is public
        - Instance to Bounce
        - Instance to nat (blackbox)
   - Second subnet is private
        - Instance for fun

Simply use setup_vpc() function in your scripts
"""

__author__      = "Heckle"
__copyright__   = "BSD"


import time
import urllib2
import json
from OCBase import OCBase, SLEEP_SHORT
from tools.wait_for import wait_state


def _create_network(ocb, vpc_cidr, subnet_public_cidr, subnet_private_cidr, tag_prefix):
    """
    Create all networks
    :param ocb: connection object
    :type ocb: OCBase.OCBase
    :param vpc_cidr: vpc cidr
    :type vpc_cidr: str
    :param subnet_public_cidr: subnet_public_cidr cidr
    :type subnet_public_cidr: str
    :param subnet_private_cidr: subnet_private_cidr cidr
    :type subnet_private_cidr: str
    :param tag_prefix: prefix to be applied on all tags
    :type tag_prefix: str
    :returns: Networks objects
    :rtype: boto.vpc.vpc.VPC, boto.vpc.vpc.SUBNET, boto.vpc.vpc.SUBNET
    """
    vpc = ocb.fcu.create_vpc(vpc_cidr)
    ocb.log('VPC {0} created'.format(vpc.id), level='info')
    time.sleep(SLEEP_SHORT)
    subnet_public = ocb.fcu.create_subnet(vpc.id, subnet_public_cidr)
    ocb.log('Subnet Public {0} created'.format(subnet_public.id), level='info')
    subnet_private = ocb.fcu.create_subnet(vpc.id, subnet_private_cidr)
    ocb.log('Subnet Private {0} created'.format(subnet_private.id), level='info')
    #
    ocb.fcu.create_tags([vpc.id], {'Name': '{0}'.format(tag_prefix)})
    ocb.fcu.create_tags([subnet_public.id], {'Name': '{0}-public'.format(tag_prefix)})
    ocb.fcu.create_tags([subnet_private.id], {'Name': '{0}-private'.format(tag_prefix)})
    return vpc, subnet_public, subnet_private

def _create_gateway(ocb, vpc):
    """
    Create Internet Gateway.
    Create Route Table for Internet Access
    Configure Main Route Table to redirect flows to NAT INSTANCE
    :param ocb: connection object
    :type ocb: OCBase.OCBase
    :param vpc: vpc
    :type vpc: boto.vpc.vpc.VPC
    :returns: Internet Gateway
    :rtype: boto.vpc.internetgateway.InternetGateway
    """
    gw = ocb.fcu.create_internet_gateway()
    time.sleep(SLEEP_SHORT)
    ocb.fcu.attach_internet_gateway(gw.id, vpc.id)
    time.sleep(SLEEP_SHORT)
    gw = ocb.fcu.get_all_internet_gateways(gw.id)[0]
    ocb.log('Internet Gateway {0} created'.format(gw.id), level='info')
    return gw

def _create_security_groups(ocb, vpc, tag_prefix):
    """
    Create Public and Private Security Group
    Public security group will allow inbound:
            - SSH from current location
            - ALL protcols on all ports from sg_private
    Private security group will allow inbound:
            - SSH from sg_public
    :param ocb: connection object
    :type ocb: OCBase.OCBase
    :param vpc: vpc
    :type vpc: boto.vpc.vpc.VPC
    :param tag_prefix: prefix to be applied on all tags
    :type tag_prefix: str
    :returns: Public and Private Security group
    :rtype: boto.ec2.securitygroup.SecurityGroup
    """
    try:
        current_location_ip = urllib2.urlopen('https://ifconfig.io/all.json').read()
        current_location_ip = '{0}/32'.format(json.loads(current_location_ip)['ip'])
    except:
        current_location_ip = '0.0.0.0/0'
    ocb.log('Public Security Group allows SSH from {0}'.format(current_location_ip), level='info')
    #
    sg_public = ocb.fcu.create_security_group('{0}-public'.format(tag_prefix), 'public security group', vpc_id=vpc.id)
    sg_private = ocb.fcu.create_security_group('{0}-private'.format(tag_prefix), 'private security group', vpc_id=vpc.id)
    #
    sg_public.authorize('tcp', 22, 22, current_location_ip)
    sg_public.authorize('tcp', 0, 65535, src_group=sg_private)
    sg_public.authorize('udp', 0, 65535, src_group=sg_private)
    sg_public.authorize('icmp', -1, -1, src_group=sg_private)
    #
    sg_private.authorize('tcp', 22, 22, src_group=sg_public)
    return sg_public, sg_private

def _run_instances(ocb, omi_id, nat_omi_id, subnet_public, subnet_private, sg_public, sg_private, key_name, instance_type, tag_prefix):
    """
    Create NAT instance if nat_omi_id is not None and BOUNCER instance in public subnet
    Create 1 instance in the private subnet
    :param ocb: connection object
    :type ocb: OCBase.OCBase
    :param subnet_public: subnet public
    :type vpc: boto.vpc.vpc.SUBNET
    :param subnet_public: subnet public
    :type subnet_public: boto.vpc.vpc.SUBNET
    :param subnet_private: subnet private
    :type subnet_private: boto.vpc.vpc.SUBNET
    :param sg_public: public security group
    :type sg_public: boto.ec2.securitygroup.SecurityGroup
    :param sg_private: private security group
    :type sg_private: boto.ec2.securitygroup.SecurityGroup
    :param tag_prefix: prefix to be applied on all tags
    :type tag_prefix: str
    :returns: 3 instances
    :rtype: boto.ec2.instance
    """
    instance_nat = None
    if nat_omi_id:
        instance_nat = ocb.fcu.run_instances(image_id=nat_omi_id,
                                             min_count=1, max_count=1,
                                             subnet_id=subnet_public.id,
                                             security_group_ids=[sg_public.id],
                                             instance_type=instance_type,
                                             key_name=key_name).instances[0]
        ocb.fcu.create_tags([instance_nat.id], {'Name': '{0}-nat'.format(tag_prefix)})
    #
    instance_bouncer = ocb.fcu.run_instances(image_id=omi_id,
                                             min_count=1, max_count=1,
                                             subnet_id=subnet_public.id,
                                             security_group_ids=[sg_public.id],
                                             instance_type=instance_type,
                                             key_name=key_name).instances[0]
    ocb.fcu.create_tags([instance_bouncer.id], {'Name': '{0}-bouncer'.format(tag_prefix)})
    #
    instance_private = ocb.fcu.run_instances(image_id=omi_id,
                                             min_count=1, max_count=1,
                                             subnet_id=subnet_private.id,
                                             security_group_ids=[sg_private.id],
                                             instance_type=instance_type,
                                             key_name=key_name).instances[0]
    ocb.fcu.create_tags([instance_private.id], {'Name': '{0}-instance-1'.format(tag_prefix)})
    wait_state([instance_nat, instance_bouncer, instance_private], 'running')
    return instance_nat, instance_bouncer, instance_private

def _configure_network_flows(ocb, vpc, subnet_public, subnet_private, gw, instance_nat):
    """
    Setup MAIN ROUTE TABLE to route flows to nat_instance
    Create RouteTable for subnet_public to route flows to internet gateway
    :param ocb: connection object
    :type ocb: OCBase.OCBase
    :param subnet_public: subnet public
    :type vpc: boto.vpc.vpc.SUBNET
    :param subnet_public: subnet public
    :type subnet_public: boto.vpc.vpc.SUBNET
    :param subnet_private: subnet private
    :type subnet_private: boto.vpc.vpc.SUBNET
    :param gw: Internet Gateway
    :type gw: boto.vpc.internetgateway.InternetGateway
    :param instance_nat: NAT Instance
    :type instance_nat: boto.ec2.instance
    """
    main_rt = ocb.fcu.get_all_route_tables(filters={'vpc-id': vpc.id, 'association.main': 'true'})[0]
    if instance_nat:
        ocb.fcu.create_route(main_rt.id, '0.0.0.0/0', gateway_id=None, instance_id=instance_nat.id)
    ocb.fcu.create_tags([main_rt.id], {'Name': 'main for {0}'.format(vpc.id)})
    #
    rt = ocb.fcu.create_route_table(vpc.id)
    ocb.fcu.create_tags([rt.id], {'Name': 'second for {0}'.format(vpc.id)})
    time.sleep(SLEEP_SHORT)
    ocb.log('Creatting Route Table {0}'.format(rt.id), level='info')
    ocb.fcu.associate_route_table(rt.id, subnet_public.id)
    time.sleep(SLEEP_SHORT)
    ocb.fcu.create_route(rt.id, '0.0.0.0/0', gateway_id=gw.id)
    # Configure NAT Instance to forward packets
    if instance_nat:
        ocb.fcu.modify_instance_attribute(instance_nat.id, attribute='sourceDestCheck', value=False)

def _setup_public_ips(ocb, instance_nat, instance_bouncer):
    """
    Create and attach 2 publics IPs to nat and bouncer instances
    :param ocb: connection object
    :type ocb: OCBase.OCBase
    :param instance_nat: NAT Instance
    :type instance_nat: boto.ec2.instance
    :param instance_bouncer: Bouncer Instance
    :type instance_bouncer: boto.ec2.instance

    """
    public_ip = ocb.fcu.allocate_address("vpc")
    if instance_nat:
        ocb.fcu.associate_address(instance_id=instance_nat.id, allocation_id=public_ip.allocation_id)
        ocb.fcu.modify_instance_attribute(instance_nat.id, attribute='sourceDestCheck', value=False)
        ocb.fcu.create_tags([instance_nat.id], {'osc.fcu.eip.auto-attach': public_ip.public_ip})
        ocb.log('NAT Instance {0} has got IP {1}'.format(instance_nat.id, public_ip.public_ip))
    #
    public_ip = ocb.fcu.allocate_address("vpc")
    ocb.fcu.associate_address(instance_id=instance_bouncer.id, allocation_id=public_ip.allocation_id)
    ocb.fcu.create_tags([instance_bouncer.id], {'osc.fcu.eip.auto-attach': public_ip.public_ip})
    ocb.log('Boucner Instance {0} has got IP {1}'.format(instance_bouncer.id, public_ip.public_ip), level='info')

def setup_vpc(omi_id, key_name, nat_omi_id=None, vpc_cidr='10.0.0.0/16', subnet_public_cidr='10.0.1.0/24', subnet_private_cidr='10.0.2.0/24', instance_type='t2.medium', tag_prefix=''):
    """
    Create a VPC with 2 subnets and a nat instance
      - First subnet is public
        - Instance to Bounce
        - Instance to nat (blackbox)
     - Second subnet is private
        - Instance for fun
    :param omi_id: OMI identified
    :type omi_id: str
    :param nat_omi_id: NAT OMI identified
    :type nat_omi_id: str
    :param key_name: key pair name
    :type key_name: str
    :param vpc_cidr: vpc cidr
    :type vpc_cidr: str
    :param subnet_public_cidr: public subnet cidr
    :type subnet_public_cidr: str
    :param subnet_private_cidr: private subnet cidr
    :type subnet_private_cidr: str
    :param tag_prefix: prefix to be applied on all tags
    :type tag_prefix: str
    """
    ocb = OCBase()
    vpc, subnet_public, subnet_private = _create_network(ocb, vpc_cidr, subnet_public_cidr, subnet_private_cidr, tag_prefix)
    gw = _create_gateway(ocb, vpc)
    sg_public, sg_private = _create_security_groups(ocb, vpc, tag_prefix)
    instance_nat, instance_bouncer, instance_private = _run_instances(ocb, omi_id, nat_omi_id, subnet_public, subnet_private, sg_public, sg_private, key_name, instance_type, tag_prefix)
    _configure_network_flows(ocb, vpc, subnet_public, subnet_private, gw, instance_nat)
    _setup_public_ips(ocb, instance_nat, instance_bouncer)
    if instance_nat:
        instance_nat.update()
    instance_bouncer.update()
    instance_private.update()
    return vpc, instance_nat, instance_bouncer, instance_private
