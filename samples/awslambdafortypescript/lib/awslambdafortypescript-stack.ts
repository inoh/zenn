import { Stack, StackProps } from 'aws-cdk-lib'
import { Runtime } from 'aws-cdk-lib/aws-lambda'
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs'
import { Construct } from 'constructs'

export class AwslambdafortypescriptStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props)

    new NodejsFunction(this, 'AwslambdafortypescriptFunction', {
      entry: 'resources/nodejsfunction/index.ts',
      handler: 'handler',
      runtime: Runtime.NODEJS_20_X,
    })
  }
}
