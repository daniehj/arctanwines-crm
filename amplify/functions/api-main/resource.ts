import { defineFunction } from "@aws-amplify/backend";
import { Duration } from "aws-cdk-lib";
import { Function, Runtime, Code } from "aws-cdk-lib/aws-lambda";
import { PolicyStatement } from "aws-cdk-lib/aws-iam";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const functionDir = path.dirname(fileURLToPath(import.meta.url));

export const apiMainFunction = defineFunction(
  (scope) => {
    // Create the FastAPI Lambda function
    const lambdaFunction = new Function(scope, "api-main", {
      handler: "handler.handler",
      runtime: Runtime.PYTHON_3_9,
      timeout: Duration.seconds(30),
      memorySize: 1024,
      code: Code.fromAsset(functionDir),
      environment: {
        // These will be set via SSM Parameter Store or environment
      }
    });

    // Add SSM permissions to read configuration parameters
    lambdaFunction.addToRolePolicy(new PolicyStatement({
      actions: [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ],
      resources: [
        `arn:aws:ssm:*:*:parameter/arctan-wines/*`
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

    return lambdaFunction;
  }
); 