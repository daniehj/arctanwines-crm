import { execSync } from "node:child_process";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { defineFunction } from "@aws-amplify/backend";
import { Duration } from "aws-cdk-lib";
import { Code, Function, Runtime, LayerVersion } from "aws-cdk-lib/aws-lambda";
import { RestApi, LambdaIntegration, AuthorizationType, MethodLoggingLevel } from "aws-cdk-lib/aws-apigateway";
import { PolicyStatement, Role, WebIdentityPrincipal, PolicyDocument, Effect } from "aws-cdk-lib/aws-iam";
import { Vpc, SecurityGroup, Port, InterfaceVpcEndpoint, InterfaceVpcEndpointAwsService } from "aws-cdk-lib/aws-ec2";

const functionDir = path.dirname(fileURLToPath(import.meta.url));

export const apiMainFunction = defineFunction(
  (scope) => {
    // Import the existing VPC and subnets by ID with CIDR block
    const vpc = Vpc.fromVpcAttributes(scope, "AuroraVpc", {
      vpcId: "vpc-05c4cb9498d87e69d",
      vpcCidrBlock: "172.31.0.0/16", // Actual VPC CIDR from AWS console
      availabilityZones: ["eu-west-1a", "eu-west-1b", "eu-west-1c"],
      privateSubnetIds: ["subnet-086978f4e594eb9ae", "subnet-095a97ab243096c24", "subnet-0b11a013be429912f"]
    });

    // Create a security group for the Lambda function
    const lambdaSecurityGroup = new SecurityGroup(scope, "lambda-sg", {
      vpc: vpc,
      description: "Security group for Lambda function to access Aurora",
      allowAllOutbound: true
    });

    // Create a security group for VPC endpoints
    const vpcEndpointSecurityGroup = new SecurityGroup(scope, "vpc-endpoint-sg", {
      vpc: vpc,
      description: "Security group for VPC endpoints to access AWS services",
      allowAllOutbound: false
    });

    // Allow HTTPS traffic from Lambda to VPC endpoints
    vpcEndpointSecurityGroup.addIngressRule(
      lambdaSecurityGroup,
      Port.tcp(443),
      "Allow Lambda to access VPC endpoints"
    );

    // Allow Lambda to access VPC endpoints (HTTPS)
    lambdaSecurityGroup.addEgressRule(
      vpcEndpointSecurityGroup,
      Port.tcp(443),
      "Allow Lambda to access AWS services via VPC endpoints"
    );

    // Create VPC endpoint for Secrets Manager (primary need)
    const secretsManagerVpcEndpoint = new InterfaceVpcEndpoint(scope, "secrets-manager-vpc-endpoint", {
      vpc: vpc,
      service: InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
      subnets: {
        subnets: vpc.privateSubnets
      },
      securityGroups: [vpcEndpointSecurityGroup],
      privateDnsEnabled: true
    });

    // Create VPC endpoint for SSM Parameter Store
    const ssmVpcEndpoint = new InterfaceVpcEndpoint(scope, "ssm-vpc-endpoint", {
      vpc: vpc,
      service: InterfaceVpcEndpointAwsService.SSM,
      subnets: {
        subnets: vpc.privateSubnets
      },
      securityGroups: [vpcEndpointSecurityGroup],
      privateDnsEnabled: true
    });

    // Create the FastAPI Lambda function
    const lambdaFunction = new Function(scope, "api-main", {
      handler: "handler.handler",
      runtime: Runtime.PYTHON_3_12,
      timeout: Duration.seconds(300),
      memorySize: 1024,
      code: Code.fromAsset(functionDir, {
        bundling: {
          image: Runtime.PYTHON_3_12.bundlingImage,
          command: [
            "bash", "-c", 
            "pip install -r requirements.txt -t /asset-output && cp *.py /asset-output/"
          ],
        },
      }),
      environment: {
        ENVIRONMENT: "production",
        PYTHONPATH: "/var/task"
      },
      // Configure VPC access to connect to Aurora
      vpc: vpc,
      vpcSubnets: {
        subnets: vpc.privateSubnets
      },
      securityGroups: [lambdaSecurityGroup]
    });

    // Add VPC execution permissions for Lambda
    lambdaFunction.addToRolePolicy(new PolicyStatement({
      actions: [
        "ec2:CreateNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface",
        "ec2:AttachNetworkInterface",
        "ec2:DetachNetworkInterface"
      ],
      resources: ["*"]
    }));

    // Allow Lambda security group to connect to Aurora on port 5432
    // Get reference to the existing Aurora security group
    const auroraSecurityGroup = SecurityGroup.fromSecurityGroupId(scope, "aurora-sg", "sg-0c0d0e7a3600397fb");
    
    // Allow Lambda to connect to Aurora
    auroraSecurityGroup.addIngressRule(
      lambdaSecurityGroup,
      Port.tcp(5432),
      "Allow Lambda to connect to Aurora PostgreSQL"
    );

    // Add SSM permissions to read configuration parameters
    lambdaFunction.addToRolePolicy(new PolicyStatement({
      actions: [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ],
      resources: [
        `arn:aws:ssm:*:*:parameter/amplify/arctanwines/*`,
        `arn:aws:ssm:*:*:parameter/amplify/arctan-wines/*`,
        `arn:aws:ssm:*:*:parameter/amplify/*`,
        `arn:aws:ssm:*:*:parameter/arctan-wines/*`
      ]
    }));

    // Add Secrets Manager permissions for database password
    lambdaFunction.addToRolePolicy(new PolicyStatement({
      actions: [
        "secretsmanager:GetSecretValue"
      ],
      resources: [
        `arn:aws:secretsmanager:*:*:secret:rds!cluster-*`
      ]
    }));

    // Add RDS permissions for database access
    lambdaFunction.addToRolePolicy(new PolicyStatement({
      actions: [
        "rds:DescribeDBInstances",
        "rds:DescribeDBClusters"
      ],
      resources: ["*"]
    }));

    // Add Lambda invoke permissions for calling db-migrations function
    lambdaFunction.addToRolePolicy(new PolicyStatement({
      actions: [
        "lambda:InvokeFunction"
      ],
      resources: [
        `arn:aws:lambda:*:*:function:amplify-*-dbMigrations*`,
        `arn:aws:lambda:*:*:function:*db-migrations*`,
        `arn:aws:lambda:*:*:function:arctanwines-db-migrations*`
      ]
    }));

    // Create REST API with AWS IAM authorization
    const api = new RestApi(scope, "arctanwines-crm-api", {
      restApiName: "arctanwines-crm-api",
      description: "Wine Import CRM API with AWS IAM authorization",
      deployOptions: {
        stageName: 'api',
        loggingLevel: MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        metricsEnabled: true
      },
      defaultCorsPreflightOptions: {
        allowOrigins: ["*"],
        allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
        allowHeaders: [
          "Content-Type", 
          "X-Amz-Date", 
          "Authorization", 
          "X-Api-Key", 
          "X-Amz-Security-Token", 
          "X-Requested-With",
          "Access-Control-Allow-Origin",
          "Access-Control-Allow-Headers",
          "Access-Control-Allow-Methods"
        ],
        allowCredentials: true,
        exposeHeaders: ["*"],
        maxAge: Duration.days(1)
      }
    });

    // Create Lambda integration
    const lambdaIntegration = new LambdaIntegration(lambdaFunction, {
      proxy: true
    });

    // Root endpoint with AWS IAM authorization
    api.root.addMethod("ANY", lambdaIntegration, {
      authorizationType: AuthorizationType.IAM
    });

    // Proxy resource for all paths with AWS IAM authorization
    const proxyResource = api.root.addResource("{proxy+}");
    proxyResource.addMethod("ANY", lambdaIntegration, {
      authorizationType: AuthorizationType.IAM
    });

    return lambdaFunction;
  },
  {
    resourceGroupName: "api-main"
  }
); 