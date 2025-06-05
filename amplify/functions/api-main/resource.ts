import { execSync } from "node:child_process";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { defineFunction } from "@aws-amplify/backend";
import { DockerImage, Duration } from "aws-cdk-lib";
import { Code, Function, Runtime } from "aws-cdk-lib/aws-lambda";
import { LambdaRestApi } from "aws-cdk-lib/aws-apigateway";
import { PolicyStatement } from "aws-cdk-lib/aws-iam";
import { Vpc, SecurityGroup, SubnetSelection, Subnet, Port, InterfaceVpcEndpoint, InterfaceVpcEndpointAwsService } from "aws-cdk-lib/aws-ec2";

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

    // Create the FastAPI Lambda function
    const lambdaFunction = new Function(scope, "api-main", {
      handler: "handler.handler",
      runtime: Runtime.PYTHON_3_12,
      timeout: Duration.seconds(300),
      memorySize: 1024,
      code: Code.fromAsset(functionDir, {
        bundling: {
          image: DockerImage.fromRegistry("dummy"),
          local: {
            tryBundle(outputDir: string) {
              // Install dependencies with platform targeting for Lambda
              execSync(
                `python3 -m pip install -r ${path.join(functionDir, "requirements.txt")} -t ${path.join(outputDir)} --platform manylinux2014_x86_64 --only-binary=:all:`
              );
              // Copy source files
              execSync(`cp -r ${functionDir}/*.py ${path.join(outputDir)}`);
              return true;
            },
          },
        },
      }),
      environment: {
        ENVIRONMENT: "production",
        PYTHONPATH: "/var/task",
        // Add database connection details as environment variables for testing
        DATABASE_HOST: "arctanwines-crm-prod.cluster-c1m6agouerh1.eu-west-1.rds.amazonaws.com",
        DATABASE_PORT: "5432",
        DATABASE_NAME: "postgres",
        DATABASE_USERNAME: "postgres",
        DATABASE_PASSWORD_SECRET: "arn:aws:secretsmanager:eu-west-1:390402552152:secret:rds!cluster-4c0ddb25-674d-4999-bf55-471ded9ed31a-5ehyNh"
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

    // Create an API Gateway for HTTP access
    const api = new LambdaRestApi(scope, "api-main-gateway", {
      handler: lambdaFunction,
      proxy: true,
      defaultCorsPreflightOptions: {
        allowOrigins: ["*"],
        allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allowHeaders: ["*"]
      }
    });

    return lambdaFunction;
  },
  {
    resourceGroupName: "api-main"
  }
); 