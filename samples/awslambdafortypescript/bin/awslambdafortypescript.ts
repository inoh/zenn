#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { AwslambdafortypescriptStack } from '../lib/awslambdafortypescript-stack';

const app = new cdk.App();
new AwslambdafortypescriptStack(app, 'AwslambdafortypescriptStack');
