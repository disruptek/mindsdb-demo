#!/usr/bin/env python3

### NOTE: There's currently no support for autocreating the security
### groups for network load balancers, so we have to instantiate the group
### ourselves.
### NOTE: Don't yet know if the same certificates need to be used internally.

import os
import base64
import aws_cdk.aws_ec2 as ec2
from aws_cdk.aws_ec2 import Port
from aws_cdk.aws_autoscaling import AutoScalingGroup
from aws_cdk.core import Stack, App, CfnOutput, Environment, Duration
from aws_cdk.aws_elasticloadbalancingv2 import \
    NetworkLoadBalancer, Protocol, NetworkTargetGroup, HealthCheck
from aws_cdk.aws_certificatemanager import Certificate, CertificateValidation
from aws_cdk.aws_route53 import CnameRecord, AaaaRecord, RecordTarget, HostedZone
from aws_cdk.aws_route53_targets import LoadBalancerTarget

###
### some constants worthy of edits
###

NAME = "MindsDemo"              # an identifier name for the stack
NOT_WEB = 27017                 # port for the (not web) service

if True:
    DOMAIN = "disruptek.com"    # the DNS domain we will query/adjust
    WEB_PORT =  80              # port for the web service
    WEB_PROT = Protocol.TCP     # protocol for the web service
    NOT_WEB_HEALTH_CHECKS = False
else:
    DOMAIN = "mindsdb.com"      # the DNS domain we will query/adjust
    WEB_PORT = 443              # port for the web service
    WEB_PROT = Protocol.TLS     # protocol for the web service
    NOT_WEB_HEALTH_CHECKS = True

HOSTNAME = "cloud." + DOMAIN    # the DNS hostname for the service

def http_service():
    """a simple http service recipe for testing"""
    data = open("./httpd.sh", "rb").read()
    httpd = ec2.UserData.for_linux()
    httpd.add_commands(str(data,'utf-8'))
    return httpd

###
### for now, just an encapsulated stack that doesn't reveal any internals
###

class DemoStack(Stack):
    def __init__(self, app: App, id: str, env: Environment) -> None:
        super().__init__(app, id, env=env)

        # start by getting the DNS zone we're going to work with
        zone = HostedZone.from_lookup(self, "Dominick",
            domain_name=DOMAIN)

        # create a certificate for the web service which matches its hostname
        cert = Certificate(self, "Cletus",
            domain_name=HOSTNAME,
            validation=CertificateValidation.from_dns(zone))

        # the services will live in a vpc, of course
        vpc = ec2.Vpc(self, "Virgil")

        # we're going to scale this web-service automatically
        asg = AutoScalingGroup(self, "Alice", vpc=vpc,
            user_data=http_service(),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE2,
                ec2.InstanceSize.MICRO),
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2))

        # explicitly allow internal access from the vpc just to be safe
        asg.connections.allow_internally(Port.tcp(WEB_PORT), "web-service")
        asg.connections.allow_internally(Port.tcp(NOT_WEB), "not-web")

        # expose the scaling group ports and permit egress
        asg.connections.allow_from_any_ipv4(Port.tcp(WEB_PORT))
        asg.connections.allow_from_any_ipv4(Port.tcp(NOT_WEB))

        # create a health check for the not-web service that currently
        if NOT_WEB_HEALTH_CHECKS:
            # points to the not-web service
            checker = HealthCheck(interval=Duration.seconds(10),
                port=NOT_WEB, protocol=Protocol.TCP)
        else:
            # points to the web port where our demo server listens
            checker = HealthCheck(interval=Duration.seconds(10),
                port=str(WEB_PORT), protocol=WEB_PROT)

        # put the scaling group behind a network target group for the LB
        notwebish = NetworkTargetGroup(self, "Allison", vpc=vpc,
            health_check=checker,
            targets=[asg],
            port=NOT_WEB, protocol=Protocol.TCP)

        # for the web-like ports, we can use the default health check
        webish = NetworkTargetGroup(self, "Alicen", vpc=vpc,
            health_check=HealthCheck(interval=Duration.seconds(10)),
            targets=[asg],
            port=WEB_PORT, protocol=WEB_PROT)

        if True:
            # create the load balancer and put it into dns
            lb = NetworkLoadBalancer(self, "Lisa", vpc=vpc,
                internet_facing=True)

            # create a hostname for the service
            CnameRecord(self, "Carl",
                domain_name=lb.load_balancer_dns_name,
                zone=zone,
                record_name=HOSTNAME.split('.')[0],
                ttl=Duration.seconds(60))
        else:
            # a multi-step deployment could allow using an alias in R53
            lb = NetworkLoadBalancer.from_network_load_balancer_attributes(self,
                "Larry", vpc=vpc,
                load_balancer_arn=some.load_balancer_arn,
                load_balancer_dns_name=HOSTNAME,
                load_balancer_canonical_hosted_zone_id=zone.hosted_zone_id)

            # create a hostname for the service
            AaaaRecord(self, "Eric",
                zone=zone,
                record_name=HOSTNAME.split('.')[0],
                target=RecordTarget.from_alias(LoadBalancerTarget(lb)))

        # point the load balancer to the target group for the ssl service
        #
        # TODO: determine if we need to use the same cert for pub-facing
        #       and internal service
        lb.add_listener("Cecil", port=443, certificates=[cert],
            default_target_groups=[webish])

        # point the load balancer to the target group for the web service
        lb.add_listener("Webster", port=80,
            default_target_groups=[webish])

        # point the load balancer to the group for the not-web service
        lb.add_listener("NotWeb",
            default_target_groups=[notwebish],
            port=NOT_WEB, protocol=Protocol.TCP)

        # auto scale the, uh, autoscaling group
        asg.scale_on_cpu_utilization("ScaleCPU", target_utilization_percent=80)

        # emit some output values, largely for console use
        CfnOutput(self, "LB", export_name="LB",
                  value=lb.load_balancer_dns_name)
        CfnOutput(self, "HTTP", export_name="HTTP",
                value="http://{}/".format(HOSTNAME))
        CfnOutput(self, "HTTPS", export_name="HTTPS",
                value="https://{}/".format(HOSTNAME))
        CfnOutput(self, "TCP", export_name="TCP",
                value="tcp://{}:{}/".format(HOSTNAME, NOT_WEB))
        CfnOutput(self, "Cert", export_name="Cert", value=cert.certificate_arn)


env = Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"],
                  region=os.environ["CDK_DEFAULT_REGION"])

app = App()
demo = DemoStack(app, NAME, env=env)
app.synth()
