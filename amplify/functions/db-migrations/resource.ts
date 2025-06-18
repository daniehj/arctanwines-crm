import { defineFunction } from '@aws-amplify/backend';
import { Duration } from 'aws-cdk-lib';
import { Code, Function, Runtime } from 'aws-cdk-lib/aws-lambda';
import { PolicyStatement } from 'aws-cdk-lib/aws-iam';
import { execSync } from 'node:child_process';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const functionDir = path.dirname(fileURLToPath(import.meta.url));

export const dbMigrationsFunction = defineFunction(
  (scope) => {
    // Create the Python Lambda function
    const lambdaFunction = new Function(scope, 'db-migrations', {
      handler: 'handler.handler',
      runtime: Runtime.PYTHON_3_12,
      timeout: Duration.seconds(300),
      memorySize: 1024,
      code: Code.fromAsset(functionDir),
      environment: {
        PYTHONPATH: '/var/task'
      }
    });

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