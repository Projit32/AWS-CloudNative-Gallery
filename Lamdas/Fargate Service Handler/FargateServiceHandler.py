import json
import os

import boto3

ecs = boto3.client('ecs')
events = boto3.client('events')
lambda_client = boto3.client('lambda')
def handler(event, context):

    # For debugging so you can see raw event format.
    print('Here is the event:')
    print((json.dumps(event)))

    if event["source"] != "aws.ecs":


        # Finding out the Service Name
        service = str(event.get("detail").get("group")).replace("service:", "")
        cluster = str(event.get('detail').get("clusterArn"))
        service_to_update = service.replace("-SPOT", "")

        if str(event['detail']['lastStatus']).upper() == "RUNNING" and str(event['detail']['desiredStatus']).upper() == "RUNNING":
            print("Spot Service for", service, "was successfully started")
            print("Shutting off On-Demand Service")
            print(ecs.update_service(cluster=cluster, service=service_to_update, desiredCount=0))

            # Deleting the Recovery Rule for the service
            response = events.list_rules(
                NamePrefix='Recovery-' + service + "-Rule"
            ).get("Rules")

            if response:
                print("Deleting the recovery rule to start SPOT task for ", service)
                events.delete_rule(
                    Name='Recovery-' + service + "-Rule",
                    Force=True
                )

                lambda_client.remove_permission(
                    FunctionName=os.getenv("FUNCTION_NAME"),
                    StatementId=service+"_permission"
                )
            else:
                print("No Rule exists for task ", service, " to be deleted!")


        elif str(event['detail']['desiredStatus']).upper() == "STOPPED":
            print("Spot Service for", service, "was Has been reclaimed!")
            print("Starting On-Demand Service")
            print(ecs.update_service(cluster=cluster, service=service_to_update, desiredCount=1))

            # Create a Recovery Rule for the service
            response = events.list_rules(
                NamePrefix='Recovery-' + service + "-Rule"
            ).get("Rules")

            if not response:
                print("Creating a new rule to start SPOT task for ", service)
                new_rule = events.put_rule(
                    Name='Recovery-' + service + "-Rule",
                    ScheduleExpression='cron(0 * * * ? *)',
                    EventPattern='string',
                    State='ENABLED',
                    Description=service + "::" + cluster
                )

                lambda_client.add_permission(
                    FunctionName=os.getenv("FUNCTION_NAME"),
                    StatementId=service+"_permission",
                    Action='lambda:InvokeFunction',
                    Principal='events.amazonaws.com',
                    SourceArn=new_rule['RuleArn']
                )
            else:
                print("Rule already exists for task ", service)



    elif event["source"] != "aws.events":
        rule_name:str =  event['resources'][0].split("/")[1]
        rule = events.describe_rule(
                    Name=rule_name,
                )
        service, cluster = rule.get("Description")
        print("Trying to start the spot service : ", service)
        print(ecs.update_service(cluster=cluster, service=service, desiredCount=1))
