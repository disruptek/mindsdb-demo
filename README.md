# Demo for MindsDB

~~This currently demonstrates a bug with attaching the certificate to one of
the network load balancer listeners.~~

I was using it wrong. Listeners need a specially-wrapped `ListenerCertificate`.

## Setup

Installing the requirements via the usual Python nonsense:

```bash
$ virtualenv py
$ . py/bin/activate.fish  # you /do/ use fish, right?
$ pip install -r requirements.txt
```

If you don't have the CDK CLI installed, you can install it globally or simply
season to taste:

```bash
$ npm install -g aws-cdk
```

## Deploy

Deploy the stack using the node-based CLI tool that is now in your path.

```bash
$ cdk deploy
```

This could fail because you've never used CDK to query resources on your
account; if it does, the error message will include the command to bootstrap
CDK and you can repeat the deploy immediately after the (quick) bootstrap
invocation.

## Measure

- You can hit http://cloud.domain.dom/ to verify that the deployment works.

- You can look in the newly-created `cdk.out` directory to examine JSON equivalent to the YAML templates you would have had to write by hand.

- You can bring up the stack for inspection in the AWS Console; navigate to _CloudFormation -> Stacks -> MindsDemo_.

## Destroy

Delete the stack and all its associated resources.

```bash
$ cdk destroy
```
