import { execSync } from "node:child_process";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { defineFunction } from "@aws-amplify/backend";
import { DockerImage, Duration } from "aws-cdk-lib";
import { Code, Function, Runtime } from "aws-cdk-lib/aws-lambda";
import { LambdaRestApi } from "aws-cdk-lib/aws-apigateway";
import { PolicyStatement } from "aws-cdk-lib/aws-iam";

const functionDir = path.dirname(fileURLToPath(import.meta.url));

export const apiMainFunction = defineFunction(
  (scope) => {
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
        PYTHONPATH: "/var/task"
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