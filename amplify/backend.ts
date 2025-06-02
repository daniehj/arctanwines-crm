import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource.js';
import { data } from './data/resource.js';
import { sayHelloFunctionHandler } from './functions/say-hello/resource';
import { apiMainFunction } from './functions/api-main/resource';

export const backend = defineBackend({
  auth,
  data,
  sayHelloFunctionHandler,
  apiMainFunction,
});

// The environment variables will be automatically injected by Amplify Gen2
// when the function has access to auth and data resources
