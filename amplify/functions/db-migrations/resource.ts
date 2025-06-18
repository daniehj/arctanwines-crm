import { defineFunction } from '@aws-amplify/backend';

export const dbMigrationsFunction = defineFunction({
  entry: './handler.py',
  timeoutSeconds: 300,
  memoryMB: 1024,
});

// Export for use in backend configuration  
export { dbMigrationsFunction as dbMigrations }; 