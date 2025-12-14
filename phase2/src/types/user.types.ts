// Permission types as per Phase 2 specification
export type Permission = 'upload' | 'search' | 'download' | 'admin';

export interface User {
  username: string;  // Primary key
  passwordHash: string;
  permissions: Permission[];  // Array of permissions
  isAdmin: boolean;  // Admin flag for convenience
  createdAt: Date;
}

export interface AuthToken {
  token: string;
  username: string;
  usageCount: number;  // Track API calls
  maxUsage: number;    // 1000 per spec
  expiresAt: Date;     // 10 hours from creation
  createdAt: Date;
}

export interface LoginRequest {
  User: {
    name: string;
    isAdmin: boolean;
  };
  Secret: {
    password: string;
  };
}

export interface RegisterRequest {
  User: {
    name: string;
    isAdmin: boolean;
  };
  Secret: {
    password: string;
  };
  permissions?: Permission[];
}