import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource.js';
import { data } from './data/resource.js';
import { sayHelloFunctionHandler } from './functions/say-hello/resource';
import { apiMainFunction } from './functions/api-main/resource';
import { dbMigrations } from './functions/db-migrations/resource';

export const backend = defineBackend({
  auth,
  data,
  sayHelloFunctionHandler,
  apiMainFunction,
  dbMigrations,
});

// Export the API configuration for the frontend
export const api = {
  name: 'arctanwines-crm-api',
  endpoints: {
    api: {
      endpoint: 'https://api.arctanwines.com/api', // This will be replaced with the actual endpoint after deployment
    },
  },
};

// The environment variables will be automatically injected by Amplify Gen2
// when the function has access to auth and data resources
