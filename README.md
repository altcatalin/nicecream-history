# Nicecream FM History

[![Build Status](https://travis-ci.org/altcatalin/nicecream-history.svg?branch=master)](https://travis-ci.org/altcatalin/nicecream-history) [![Coverage Status](https://coveralls.io/repos/github/altcatalin/nicecream-history/badge.svg?branch=master)](https://coveralls.io/github/altcatalin/nicecream-history?branch=master) [![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/altcatalin/nicecream-history/badges/quality-score.png?b=master)](https://scrutinizer-ci.com/g/altcatalin/nicecream-history/?branch=master)

If you are a [nicecream.fm](https://nicecream.fm) addict, I got you covered. You can now have all those songs playing each and every minute, even when you are not online :grin:.  

The web app is made of an [API](https://github.com/altcatalin/nicecream-history) and a [SPA](https://github.com/altcatalin/nicecream-history-spa).  

Live: [SPA](https://nh.altcatalin.com) - [API](https://nh-api.altcatalin.com)  

**Features**:

- [x] Channels history
- [x] Social sign in with Google
- [x] Bookmarks
- [ ] ...

*References*:

- [OAuth2 Implicit Grant and SPA](https://auth0.com/blog/oauth2-implicit-grant-and-spa/)  
- [Using OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/OAuth2WebServer)  
- [Swagger Cookie Authentication](https://swagger.io/docs/specification/authentication/cookie-authentication/)  

## Deployment

### Local (Docker)

**Requirements**:

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [GPC account](https://cloud.google.com/)
- Google OAuth2 client with `http://api.lvh.me:8080/user/google/callback` added to Authorized redirect URIs

Build the `api` image:  
`docker-compose build api`

Generate a Fernet secret key that will be used to encrypt the session cookie:  
`docker run --rm nicecream_history_api python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`  

Copy `.env.sample` to `.env` and fill in `API_SESSION_COOKIE_SECRET_KEY`, `API_GOOGLE_CLIENT_ID`, `API_GOOGLE_CLIENT_SECRET`:  
`cp .env.sample .env`  

Run and open `http://api.lvh.me:8080` in browser:  
`docker-compose up -d`

*References*:
- [ngrok, lvh.me and nip.io: A Trilogy for Local Development and Testing](https://nickjanetakis.com/blog/ngrok-lvhme-nipio-a-trilogy-for-local-development-and-testing)  


### AWS

Describe and provision infrastructure with CloudFormation.

**Requirements**:

- Internet domain (i.e example.com) and access to DNS management :sunglasses:  
- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [GPC account](https://cloud.google.com/)
- Google OAuth2 client with `https://api.[example.com]/user/google/callback` added to Authorized redirect URIs
- [AWS account](https://aws.amazon.com/console/)
- [AWS CLI](https://aws.amazon.com/cli/)
- AWS certificate for `*.example.com` generated into the region where deployment will be done.

*References*:

- [cloudonaut.io templates](https://templates.cloudonaut.io/en/stable/)

#### CloudFormation

The bucket will hold all CloudFormation templates.  

```bash
aws cloudformation create-stack \
--stack-name [CLOUDFORMATION_STACK_NAME] \
--template-body file://cloudformation/templates/s3.yaml \
--parameters \
    ParameterKey=Access,ParameterValue=PublicRead \
    ParameterKey=EnvironmentName,ParameterValue=[ENVIRONMENT_NAME] \
--capabilities CAPABILITY_IAM
```

Upload:  
`aws s3 sync ./cloudformation/templates s3://[CLOUDFORMATION_BUCKET]`  

#### Alert

Receive alerts from resources. Supported transports are: Slack, Email, HTTP endpoint, HTTPS endpoint

```bash
aws cloudformation create-stack \
--stack-name [ALERT_STACK_NAME] \
--template-url https://s3.amazonaws.com/[CLOUDFORMATION_BUCKET]/alert.yaml \
--parameters \
    ParameterKey=FallbackEmail,ParameterValue=[FALLBACK_EMAIL] \
    ParameterKey=Email,ParameterValue=[EMAIL] \
--capabilities CAPABILITY_IAM
```

```bash
./slack_alert_lambda.sh [SLACK_LAMBDA_FUNCTION_NAME]
```

#### VPC

VPC with 2 public & 2 private subnets in two availability zones (Zone A & B).   

```bash
aws cloudformation create-stack \
--stack-name [VPC_STACK_NAME] \
--template-url https://s3.amazonaws.com/[CLOUDFORMATION_BUCKET]/vpc-2azs.yaml \
--parameters \
    ParameterKey=EnvironmentName,ParameterValue=[ENVIRONMENT_NAME]
```

#### Client Security Group

Security group used for gaining access to resources which are not integrated into the VPC (i.e ElastiCache). 

```bash
aws cloudformation create-stack \
--stack-name [CLIENT_SG_STACK_NAME] \
--template-url https://s3.amazonaws.com/[CLOUDFORMATION_BUCKET]/client-sg.yaml \
--parameters \
    ParameterKey=ParentVPCStack,ParameterValue=[VPC_STACK_NAME] \
    ParameterKey=EnvironmentName,ParameterValue=[ENVIRONMENT_NAME]
```

#### VPC EC2 NAT/SSH Bastion 

EC2 instance used for NAT and as a SSH Bastion (optional).  
Best practices recommends to have one independent stack for each availability zone.  

*NAT (per availability zone)*:  

Must deploy for each zone A & B.  

```bash
aws cloudformation create-stack \
--stack-name [VPC_NAT_STACK_NAME] \
--template-url https://s3.amazonaws.com/[CLOUDFORMATION_BUCKET]/vpc-nat-instance.yaml \
--parameters \
    ParameterKey=ParentVPCStack,ParameterValue=[VPC_STACK_NAME] \
    ParameterKey=ParentAlertStack,ParameterValue=[ALERT_STACK_NAME] \
    ParameterKey=SubnetZone,ParameterValue=[SUBNET_ZONE] \
    ParameterKey=EnvironmentName,ParameterValue=[ENVIRONMENT_NAME] \
--capabilities CAPABILITY_IAM
```

*NAT (per VPC)*:   

```bash
aws cloudformation create-stack \
--stack-name [VPC_NAT_STACK_NAME] \
--template-url https://s3.amazonaws.com/[CLOUDFORMATION_BUCKET]/vpc-nat-instance.yaml \
--parameters \
    ParameterKey=ParentVPCStack,ParameterValue=[VPC_STACK_NAME] \
    ParameterKey=ParentAlertStack,ParameterValue=[ALERT_STACK_NAME] \
    ParameterKey=EnvironmentName,ParameterValue=[ENVIRONMENT_NAME] \
--capabilities CAPABILITY_IAM
```

*NAT and SSH (per VPC)*:  

```bash
aws cloudformation create-stack \
--stack-name [VPC_NAT_STACK_NAME] \
--template-url https://s3.amazonaws.com/[CLOUDFORMATION_BUCKET]/vpc-nat-instance.yaml \
--parameters \
    ParameterKey=ParentVPCStack,ParameterValue=[VPC_STACK_NAME] \
    ParameterKey=ParentAlertStack,ParameterValue=[ALERT_STACK_NAME] \
    ParameterKey=ParentClientStack,ParameterValue=[CLIENT_SG_STACK_NAME] \
    ParameterKey=KeyName,ParameterValue=[EC2_KEY_NAME] \
    ParameterKey=SSHAccessCidrIp,ParameterValue='[IPv4_SSH_ALLOWED]/32' \
    ParameterKey=EnvironmentName,ParameterValue=[ENVIRONMENT_NAME] \
--capabilities CAPABILITY_IAM
```

#### RDS PostgresSQL

Multi-AZ/Replica disabled by default.  

```bash
aws cloudformation create-stack \
--stack-name [RDS_STACK_NAME] \
--template-url https://s3.amazonaws.com/[CLOUDFORMATION_BUCKET]/rds-postgres.yaml \
--parameters \
    ParameterKey=ParentVPCStack,ParameterValue=[VPC_STACK_NAME] \
    ParameterKey=ParentClientStack,ParameterValue=[CLIENT_SG_STACK_NAME] \
    ParameterKey=ParentAlertStack,ParameterValue=[ALERT_STACK_NAME] \
    ParameterKey=EnvironmentName,ParameterValue=[ENVIRONMENT_NAME] \
    ParameterKey=DBMasterUsername,ParameterValue=[DATABASE_USERNAME] \
    ParameterKey=DBMasterUserPassword,ParameterValue=[DATABASE_PASSWORD] \
    ParameterKey=DBName,ParameterValue=[DATABASE_NAME]
```

#### ElastiCache Redis

Multi-AZ/Replica disabled by default.  

```bash
aws cloudformation create-stack \
--stack-name [ELASTICACHE_STACK_NAME] \
--template-url https://s3.amazonaws.com/[CLOUDFORMATION_BUCKET]/elasticache-redis.yaml \
--parameters \
    ParameterKey=ParentVPCStack,ParameterValue=[VPC_STACK_NAME] \
    ParameterKey=ParentClientStack,ParameterValue=[CLIENT_SG_STACK_NAME] \
    ParameterKey=ParentAlertStack,ParameterValue=[ALERT_STACK_NAME] \
    ParameterKey=EnvironmentName,ParameterValue=[ENVIRONMENT_NAME]
```

#### EC2 ALB access logs

```bash
aws cloudformation create-stack \
--stack-name [S3_ACCESS_LOG_STACK_NAME] \
--template-url https://s3.amazonaws.com/[CLOUDFORMATION_BUCKET]/s3.yaml \
--parameters \
    ParameterKey=Access,ParameterValue=ElbAccessLogWrite \
    ParameterKey=EnvironmentName,ParameterValue=[ENVIRONMENT_NAME] \
--capabilities CAPABILITY_IAM
```

#### ECS cluster

ECS Cluster with one public ALB.  

Cluster autoscaling based on [A better solution to ECS AutoScaling](https://garbe.io/blog/2017/04/12/a-better-solution-to-ecs-autoscaling/). Things to consider: 
- maximum memory (default=256MiB) and maximum CPU (default=256Units)
- container shortage (default=0) and excess (default=4) thresholds
- instance type (default=t2.micro)

```bash
aws cloudformation create-stack \
--stack-name [ECS_STACK_NAME] \
--template-url https://s3.amazonaws.com/[CLOUDFORMATION_BUCKET]/ecs-cluster.yaml \
--parameters \
    ParameterKey=ParentVPCStack,ParameterValue=[VPC_STACK_NAME] \
    ParameterKey=ParentAlertStack,ParameterValue=[ALERT_STACK_NAME] \
    ParameterKey=ParentClientStackOne,ParameterValue=[CLIENT_SG_STACK_NAME] \
    ParameterKey=ParentS3StackAccessLog,ParameterValue=[S3_ACCESS_LOG_STACK_NAME] \
    ParameterKey=SubnetsReach,ParameterValue=Private \
    ParameterKey=SSMParametersPrefix,ParameterValue=\"[AWS_SSM_PREFIX]\" \
    ParameterKey=LoadBalancerCertificateArn,ParameterValue=[SSL_CERTIFICATE_ARN] \
    ParameterKey=EnvironmentName,ParameterValue=[ENVIRONMENT_NAME] \
--capabilities CAPABILITY_IAM
```

Add a CNAME record for `api.example.com`, pointing to ECS cluster ALB:  
`api.example.com.	3600	IN	CNAME	XXX.YYY.elb.amazonaws.com.`

#### ECS services

##### KMS parameters encryption key

Encryption key used on SSM parameters encryption.  

```bash
aws cloudformation create-stack \
--stack-name [KMS_STACK_NAME] \
--template-url https://s3.amazonaws.com/[CLOUDFORMATION_BUCKET]/kms.yaml \
--parameters \
    ParameterKey=ParentVPCStack,ParameterValue=[VPC_STACK_NAME] \
    ParameterKey=ParentClusterStack,ParameterValue=[ECS_STACK_NAME] \
    ParameterKey=Administrators,ParameterValue=\"$(aws iam get-group --group-name [IAM_GROUP] --output text | awk 'BEGIN {FS="\t";ORS=","} {print $2}' | sed 's/,$//')\" \
    ParameterKey=EnvironmentName,ParameterValue=[ENVIRONMENT_NAME]
```

##### Parameters

Check `.env.sample` and `api/settings.py` for needed parameters.  
Required parameters for production:  
- PGHOST (String)
- PGPORT (String)
- PGUSER (String)
- PGPASSWORD (SecureString)
- PGDATABASE (String)
- REDIS_HOST (String)
- REDIS_PORT (String)
- SPA_URL (String)
- API_SESSION_COOKIE_SECRET_KEY (SecureString)
- API_SESSION_COOKIE_DOMAIN (String)
- API_GOOGLE_CLIENT_ID (String)
- API_GOOGLE_CLIENT_SECRET (SecureString)
- API_GOOGLE_REDIRECT_URL (String)
- API_CSRF_COOKIE_DOMAIN (String)
- API_CORS_ALLOWED (String)
- API_CORS_ORIGIN (String)

```bash
aws ssm put-parameter \
--name "/[AWS_SSM_PREFIX]/[PARAMETER_NAME]" \
--type "String" \
--value "[PARAMETER_VALUE]"
```

```bash
aws ssm put-parameter \
--name "/[AWS_SSM_PREFIX]/[PARAMETER_NAME]" \
--type "SecureString" \
--value "[PARAMETER_VALUE]" \
--key-id [KMS_KEY_ID]
```

##### ECR

Create an [ECR repository](https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-create.html) and upload the API image before starting ECS services.  

```bash
$(aws ecr get-login --no-include-email --region [AWS_REGION])

docker build \
--tag [REPOSITORY_NAME]:latest \
--tag [REPOSITORY_NAME]:$(echo $(git rev-parse --short HEAD)) .

docker push [REPOSITORY_NAME]:latest && \
docker push [REPOSITORY_NAME]:$(echo $(git rev-parse --short HEAD))
```

##### Database migrations

Migrations task definition. Uses the same API Docker image.  

```bash
aws cloudformation create-stack \
--stack-name [MIGRATIONS_TASK_STACK_NAME] \
--template-url https://s3.amazonaws.com/[CLOUDFORMATION_BUCKET]/ecs-task.yaml \
--parameters \
    ParameterKey=ParentClusterStack,ParameterValue=[ECS_STACK_NAME] \
    ParameterKey=Image,ParameterValue=[REPOSITORY_NAME]:latest \
    ParameterKey=SSMParametersPrefix,ParameterValue=\"[AWS_SSM_PREFIX]\" \
    ParameterKey=Command,ParameterValue=\"alembic,upgrade,head\"
```

```bash
aws ecs run-task \
--cluster [ECS_CLUSTER_NAME] \
--task-definition [MIGRATIONS_TASK_STACK_NAME]
```

##### Crawler service

Uses the same API Docker image.  
Default maximum memory = 256MiB and default maximum CPU = 256Units.  
Review ECS Cluster autoscaling on maximum memory & CPU changes.   

```bash
aws cloudformation create-stack \
--stack-name [CRAWLER_SERVICE_STACK_NAME] \
--template-url https://s3.amazonaws.com/[CLOUDFORMATION_BUCKET]/ecs-service-worker.yaml \
--parameters \
    ParameterKey=ParentClusterStack,ParameterValue=[ECS_STACK_NAME] \
    ParameterKey=ParentAlertStack,ParameterValue=[ALERT_STACK_NAME] \
    ParameterKey=DesiredCount,ParameterValue=1 \
    ParameterKey=MinCapacity,ParameterValue=1 \
    ParameterKey=MaxCapacity,ParameterValue=1 \
    ParameterKey=Image,ParameterValue=[REPOSITORY_NAME]:latest \
    ParameterKey=SSMParametersPrefix,ParameterValue=\"[AWS_SSM_PREFIX]\" \
    ParameterKey=Command,ParameterValue=\"python,-m,crawler\" \
--capabilities CAPABILITY_IAM
```

##### API service

Default maximum memory = 256MiB and default maximum CPU = 256Units.  
Review ECS Cluster autoscaling on maximum memory & CPU changes.   

```bash
aws cloudformation create-stack \
--stack-name [API_SERVICE_STACK_NAME] \
--template-url https://s3.amazonaws.com/[CLOUDFORMATION_BUCKET]/ecs-service.yaml \
--parameters \
    ParameterKey=ParentVPCStack,ParameterValue=[VPC_STACK_NAME] \
    ParameterKey=ParentClusterStack,ParameterValue=[ECS_STACK_NAME] \
    ParameterKey=ParentAlertStack,ParameterValue=[ALERT_STACK_NAME] \
    ParameterKey=Image,ParameterValue=[REPOSITORY_NAME]:latest \
    ParameterKey=SSMParametersPrefix,ParameterValue=\"[AWS_SSM_PREFIX]\" \
    ParameterKey=HealthCheckPath,ParameterValue=channels \
    ParameterKey=LoadBalancerHttps,ParameterValue=true \
--capabilities CAPABILITY_IAM
```

Update:  
```bash
aws ecs update-service \
--cluster [ECS_CLUSTER_NAME] \
--force-new-deployment \
--service [ECS_SERVICE_NAME]
```
