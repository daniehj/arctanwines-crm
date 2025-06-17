import { defineFunction } from '@aws-amplify/backend';

export const dbMigrationsFunction = defineFunction({
  name: 'db-migrations',
  entry: './handler.py',
  runtime: 'python3.12',
  timeout: 300, // 5 minutes for migrations
  memoryMB: 1024,
  environment: {
    // Environment variables will be set by Amplify
  },
});

// Export for use in backend configuration
export { dbMigrationsFunction as dbMigrations }; 