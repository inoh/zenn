import { Handler } from "aws-cdk-lib/aws-lambda"

interface EventProps {
  name: string;
}

export const handler: Handler = async (event: EventProps) => {
  console.log('Hello, world!', JSON.stringify(event))
}
