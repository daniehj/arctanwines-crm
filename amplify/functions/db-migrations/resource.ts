import { defineFunction } from '@aws-amplify/backend';
import { Duration, DockerImage } from 'aws-cdk-lib';
import { Code, Function, Runtime } from 'aws-cdk-lib/aws-lambda';
import { PolicyStatement } from 'aws-cdk-lib/aws-iam';
import { Vpc, SecurityGroup, Port, InterfaceVpcEndpoint, InterfaceVpcEndpointAwsService } from 'aws-cdk-lib/aws-ec2';
import { execSync } from 'node:child_process';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const functionDir = path.dirname(fileURLToPath(import.meta.url));

export const dbMigrationsFunction = defineFunction(
  (scope) => {
    // Import the existing VPC and subnets by ID with CIDR block
    const vpc = Vpc.fromVpcAttributes(scope, "DbMigrationsVpc", {
      vpcId: "vpc-05c4cb9498d87e69d",
      vpcCidrBlock: "172.31.0.0/16",
      availabilityZones: ["eu-west-1a", "eu-west-1b", "eu-west-1c"],
      privateSubnetIds: ["subnet-086978f4e594eb9ae", "subnet-095a97ab243096c24", "subnet-0b11a013be429912f"]
    });

    // Create a security group for the Lambda function
    const lambdaSecurityGroup = new SecurityGroup(scope, "db-migrations-lambda-sg", {
      vpc: vpc,
      description: "Security group for db-migrations Lambda function to access Aurora",
      allowAllOutbound: true
    });

    // Get reference to the existing Aurora security group and allow connection
    const auroraSecurityGroup = SecurityGroup.fromSecurityGroupId(scope, "db-migrations-aurora-sg", "sg-0c0d0e7a3600397fb");
    auroraSecurityGroup.addIngressRule(
      lambdaSecurityGroup,
      Port.tcp(5432),
      "Allow db-migrations Lambda to connect to Aurora PostgreSQL"
    );

    // Create a security group for VPC endpoints
    const vpcEndpointSecurityGroup = new SecurityGroup(scope, "db-migrations-vpc-endpoint-sg", {
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

    // Create VPC endpoint for Secrets Manager
    const secretsManagerVpcEndpoint = new InterfaceVpcEndpoint(scope, "db-migrations-secrets-manager-vpc-endpoint", {
      vpc: vpc,
      service: InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
      subnets: {
        subnets: vpc.privateSubnets
      },
      securityGroups: [vpcEndpointSecurityGroup],
      privateDnsEnabled: true
    });

    // Create VPC endpoint for SSM Parameter Store
    const ssmVpcEndpoint = new InterfaceVpcEndpoint(scope, "db-migrations-ssm-vpc-endpoint", {
      vpc: vpc,
      service: InterfaceVpcEndpointAwsService.SSM,
      subnets: {
        subnets: vpc.privateSubnets
      },
      securityGroups: [vpcEndpointSecurityGroup],
      privateDnsEnabled: true
    });

    // Create the Python Lambda function
    const lambdaFunction = new Function(scope, 'db-migrations', {
      handler: 'handler.handler',
      runtime: Runtime.PYTHON_3_12,
      timeout: Duration.seconds(300),
      memorySize: 1024,
      code: Code.fromAsset(functionDir),
      environment: {
        PYTHONPATH: '/var/task'
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

    // Add SSM permissions to read configuration parameters
    lambdaFunction.addToRolePolicy(new PolicyStatement({
      actions: [
        'ssm:GetParameter',
        'ssm:GetParameters',
        'ssm:GetParametersByPath'
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
        'secretsmanager:GetSecretValue'
      ],
      resources: [
        `arn:aws:secretsmanager:*:*:secret:rds!cluster-*`
      ]
    }));

    // Add RDS permissions for database access
    lambdaFunction.addToRolePolicy(new PolicyStatement({
      actions: [
        'rds:DescribeDBInstances',
        'rds:DescribeDBClusters'
      ],
      resources: ['*']
    }));

    return lambdaFunction;
  }
);

// Export for use in backend configuration  
export { dbMigrationsFunction as dbMigrations }; 