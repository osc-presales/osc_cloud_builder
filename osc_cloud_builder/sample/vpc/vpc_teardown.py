#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Destroy a VPC and all attached ressources
"""

__author__      = "Heckle"
__copyright__   = "BSD"


import time
import re
from lxml import etree
from osc_cloud_builder.OCBase import OCBase, SLEEP_SHORT
from osc_cloud_builder.tools.wait_for import wait_state
from boto.exception import EC2ResponseError

def teardown(vpc_to_delete, terminate_instances=False):
    """
    Clean all ressouces attached to the vpc_to_delete
    :param vpc_to_delete: vpc id to delete
    :type vpc_to_delete: str
    :param terminate_instances: continue teardown even if instances exists in the VPC
    :type terminate_instances: bool
    """
    ocb = OCBase()

    if terminate_instances is False and \
       ocb.fcu.get_only_instances(filters={'vpc-id': vpc_to_delete, 'instance-state-name': 'running'}) and \
       ocb.fcu.get_only_instances(filters={'vpc-id': vpc_to_delete, 'instance-state-name': 'stopped'}) :
        ocb.log('Instances are still exists in {0}, teardown will not be executed'.format(vpc_to_delete) ,'error')
        return

    ocb.log('Deleting VPC {0}'.format(vpc_to_delete), 'info', __file__)
    vpc_instances = ocb.fcu.get_only_instances(filters={'vpc-id': vpc_to_delete})
    ocb.log('Termating VMs {0}'.format(vpc_instances), 'info')

    # Stop instances
    if [instance for instance in vpc_instances if instance.state != 'stopped' or instance.state != 'terminated']:
        try:
            ocb.fcu.stop_instances([instance.id for instance in vpc_instances])
        except EC2ResponseError as err:
            ocb.log('Stop instance error: {0}'.format(err.message), 'warning')

    time.sleep(SLEEP_SHORT)

    # Force stop instances (if ACPI STOP does not work)
    if [instance for instance in vpc_instances if instance.state != 'stopped' or instance.state != 'terminated']:
        try:
            ocb.fcu.stop_instances([instance.id for instance in vpc_instances], force=True)
        except EC2ResponseError as err:
            ocb.log('Force stop instance error: {0}'.format(err.message), 'warning')

    # Wait instance to be stopped
    wait_state(vpc_instances, 'stopped')

    # Terminate instances
    if [instance for instance in vpc_instances if instance.state != 'terminated']:
        try:
            ocb.fcu.terminate_instances([instance.id for instance in vpc_instances])
        except EC2ResponseError as err:
            ocb.log('Terminate instance error: {0}'.format(err.message), 'warning')

    # Wait instance to be terminated
    wait_state(vpc_instances, 'terminated')

    # Delete VPC-Peering connections
    for peer in ocb.fcu.get_all_vpc_peering_connections(filters={'requester-vpc-info.vpc-id': vpc_to_delete}):
        peer.delete()

    # Release EIPs
    for instance in vpc_instances:
        addresses = ocb.fcu.get_all_addresses(filters={'instance-id': instance.id})
        for address in addresses:
            try:
                ocb.fcu.disassociate_address(association_id=address.association_id)
            except EC2ResponseError as err:
                ocb.log('Disassociate EIP error: {0}'.format(err.message), 'warning')
            time.sleep(SLEEP_SHORT)
            try:
                ocb.fcu.release_address(allocation_id=address.allocation_id)
            except EC2ResponseError as err:
                ocb.log('Release EIP error: {0}'.format(err.message), 'warning')

        time.sleep(SLEEP_SHORT)

    # Flush all nic
    for nic in ocb.fcu.get_all_network_interfaces(filters={'vpc-id': vpc_to_delete}):
        nic.delete()


    # Delete internet gateways
    for gw in ocb.fcu.get_all_internet_gateways(filters={'attachment.vpc-id': vpc_to_delete}):
        for attachment in gw.attachments:
            ocb.fcu.detach_internet_gateway(gw.id, attachment.vpc_id)
            time.sleep(SLEEP_SHORT)
        ocb.fcu.delete_internet_gateway(gw.id)

    time.sleep(SLEEP_SHORT)

    try:
        # Delete nat gateways
        # Note : Can not manage multiple natgateway for now
        ocb.fcu.APIVersion = '2017-01-01'
        nat_gateway = ocb.fcu.make_request('DescribeNatGateways', params={'Filter.1.Name': 'vpc-id', 'Filter.1.Value.1': vpc_to_delete}).read()
        nat_gateway = re.sub('xmlns=\"[\S]*\"', '', nat_gateway).split('\n')[1]
        tree = etree.fromstring(nat_gateway)
        nat_gateway_id = tree.find('natGatewaySet').find('item').find('natGatewayId').text
        ocb.fcu.make_request('DeleteNatGateway', params={'NatGatewayId': nat_gateway_id})
    except:
        pass

    # Delete routes
    for rt in ocb.fcu.get_all_route_tables(filters={'vpc-id': vpc_to_delete}):
        for route in rt.routes:
            if route.gateway_id != 'local':
                ocb.fcu.delete_route(rt.id, route.destination_cidr_block)


    # Delete Load Balancers
    if ocb.lbu:
        subnets = set([sub.id for sub in ocb.fcu.get_all_subnets(filters={'vpc-id': vpc_to_delete})])
        for lb in [lb for lb in ocb.lbu.get_all_load_balancers() if set(lb.subnets).intersection(subnets)]:
            lb.delete()
            time.sleep(SLEEP_SHORT)

        # Wait for load balancers to disapear
        for i in range(1, 42):          # 42 ? Because F...
            lbs = [lb for lb in ocb.lbu.get_all_load_balancers() if set(lb.subnets).intersection(subnets)]
            if not lbs:
                break
            time.sleep(SLEEP_SHORT)

    for vpc in ocb.fcu.get_all_vpcs([vpc_to_delete]):
        # Delete route tables
        for route_table in ocb.fcu.get_all_route_tables(filters={'vpc-id': vpc.id}):
            for association in route_table.associations:
                if association.subnet_id:
                    ocb.fcu.disassociate_route_table(association.id)
        for route_table in [route_table for route_table
                            in ocb.fcu.get_all_route_tables(filters={'vpc-id': vpc.id})
                            if len([association for association in route_table.associations if association.main]) == 0]:
            ocb.fcu.delete_route_table(route_table.id)

        # Delete subnets
        for subnet in ocb.fcu.get_all_subnets(filters={'vpc-id': vpc.id}):
            ocb.fcu.delete_subnet(subnet.id)

    time.sleep(SLEEP_SHORT)

    # Flush all rules
    for group in ocb.fcu.get_all_security_groups(filters={'vpc-id': vpc.id}):
        for rule in group.rules:
            for grant in rule.grants:
                ocb.fcu.revoke_security_group(group_id=group.id, ip_protocol=rule.ip_protocol, from_port=rule.from_port, to_port=rule.to_port, src_security_group_group_id=grant.group_id, cidr_ip=grant.cidr_ip)
            for rule in group.rules_egress:
                for grant in rule.grants:
                    ocb.fcu.revoke_security_group_egress(group.id, rule.ip_protocol, rule.from_port, rule.to_port, grant.group_id, grant.cidr_ip)

    # Delete Security Groups
    for sg in ocb.fcu.get_all_security_groups(filters={'vpc-id': vpc.id}):
        if 'default' not in sg.name:
            try:
                ocb.fcu.delete_security_group(group_id=sg.id)
            except EC2ResponseError as err:
                ocb.log('Can not delete Security Group: {0}'.format(err.message), 'warning')


    # Delete VPC
    try:
        ocb.fcu.delete_vpc(vpc.id)
    except EC2ResponseError as err:
        ocb.log('Can not delete VPC: {0}'.format(err.message), 'error')
