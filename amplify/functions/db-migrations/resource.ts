import { defineFunction } from '@aws-amplify/backend';
import { Duration, DockerImage } from 'aws-cdk-lib';
import { Code, Function, Runtime } from 'aws-cdk-lib/aws-lambda';
import { PolicyStatement } from 'aws-cdk-lib/aws-iam';
import { execSync } from 'node:child_process';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const functionDir = path.dirname(fileURLToPath(import.meta.url));

export const dbMigrationsFunction = defineFunction(
  (scope) => {
    // VPC configuration will be done manually in AWS console to avoid CDK context issues

    // Create the Python Lambda function
    const lambdaFunction = new Function(scope, 'db-migrations', {
      handler: 'handler.handler',
      runtime: Runtime.PYTHON_3_12,
      timeout: Duration.seconds(300),
      memorySize: 1024,
      code: Code.fromAsset(functionDir),
      environment: {
        ENVIRONMENT: "production",
        PYTHONPATH: '/var/task',
      },
      // VPC configuration will be added manually in AWS console
    });

    // VPC execution permissions will be added automatically when VPC is configured manually

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