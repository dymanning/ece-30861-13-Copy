/**
 * TypeScript types matching ECE 461 Phase 2 OpenAPI Specification v3.3.1
 */

// ============================================
// Core Artifact Types
// ============================================

export type ArtifactType = 'model' | 'dataset' | 'code';

export interface ArtifactMetadata {
  name: string;
  id: string;
  type: ArtifactType;
}

export interface ArtifactData {
  url: string;
}

export interface Artifact {
  metadata: ArtifactMetadata;
  data: ArtifactData;
}

// ============================================
// Extended Spec Types (Rating, Cost, Lineage)
// ============================================

export interface SizeScore {
  raspberry_pi: number;
  jetson_nano: number;
  desktop_pc: number;
  aws_server: number;
}

export interface ModelRating {
  name: string;
  category: string;
  net_score: number;
  net_score_latency: number;
  ramp_up_time: number;
  ramp_up_time_latency: number;
  bus_factor: number;
  bus_factor_latency: number;
  performance_claims: number;
  performance_claims_latency: number;
  license: number;
  license_latency: number;
  dataset_and_code_score: number;
  dataset_and_code_score_latency: number;
  dataset_quality: number;
  dataset_quality_latency: number;
  code_quality: number;
  code_quality_latency: number;
  reproducibility: number;
  reproducibility_latency: number;
  reviewedness: number;
  reviewedness_latency: number;
  tree_score: number;
  tree_score_latency: number;
  size_score: SizeScore;
  size_score_latency: number;
}

export interface ArtifactCostEntry {
  standalone_cost?: number;
  total_cost: number;
}
export type ArtifactCost = Record<string, ArtifactCostEntry>;

export interface ArtifactLineageNode {
  artifact_id: string;
  name: string;
  source: string;
  metadata?: Record<string, any>;
}

export interface ArtifactLineageEdge {
  from_node_artifact_id: string;
  to_node_artifact_id: string;
  relationship: string;
}

export interface ArtifactLineageGraph {
  nodes: ArtifactLineageNode[];
  edges: ArtifactLineageEdge[];
}

// ============================================
// Query Types
// ============================================

export interface ArtifactQuery {
  name: string;  // Use "*" to enumerate all
  types?: ArtifactType[];  // Optional type filter
}

export interface ArtifactRegEx {
  regex: string;
}

// ============================================
// Pagination Types
// ============================================

export type EnumerateOffset = string;

export interface PaginationParams {
  offset: number;
  limit: number;
}

export interface PaginationResult<T> {
  items: T[];
  nextOffset: string | null;
  hasMore: boolean;
}

// ============================================
// Database Entity Types
// ============================================

export interface ArtifactEntity {
  id: string;
  name: string;
  type: ArtifactType;
  url: string;
  readme: string | null;
  metadata: Record<string, any>;
  created_at: Date;
  updated_at: Date;
}

// ============================================
// Request/Response Types
// ============================================

export interface EnumerateArtifactsRequest {
  queries: ArtifactQuery[];
  offset?: string;
}

export interface EnumerateArtifactsResponse {
  artifacts: ArtifactMetadata[];
  nextOffset: string | null;
}

export interface SearchByRegexRequest {
  regex: string;
}

export interface SearchByRegexResponse {
  artifacts: ArtifactMetadata[];
}

export interface SearchByNameResponse {
  artifacts: ArtifactMetadata[];
}

// ============================================
// Authentication Types
// ============================================

export interface User {
  name: string;
  is_admin: boolean;
}

export interface UserAuthenticationInfo {
  password: string;
}

export interface AuthenticationRequest {
  user: User;
  secret: UserAuthenticationInfo;
}

export type AuthenticationToken = string;

// ============================================
// Error Response Types
// ============================================

export interface ErrorResponse {
  error: string;
  message: string;
  statusCode: number;
}

// ============================================
// Database Query Result Types
// ============================================

export interface QueryResult<T> {
  rows: T[];
  rowCount: number;
}

// ============================================
// Configuration Types
// ============================================

export interface DatabaseConfig {
  host: string;
  port: number;
  database: string;
  user: string;
  password: string;
  ssl: boolean;
  max: number;
  idleTimeoutMillis: number;
  connectionTimeoutMillis: number;
}

export interface PaginationConfig {
  defaultPageSize: number;
  maxPageSize: number;
  maxTotalResults: number;
}

export interface RegexConfig {
  maxPatternLength: number;
  timeoutMs: number;
  maxResults: number;
}

export interface AppConfig {
  port: number;
  nodeEnv: string;
  database: DatabaseConfig;
  pagination: PaginationConfig;
  regex: RegexConfig;
  logging: {
    level: string;
    file: string;
  };
  auth: {
    enabled: boolean;
    jwtSecret: string;
  };
  features?: {
    enableBedrock: boolean;
  };
}

// ============================================
// Utility Types
// ============================================

export type Nullable<T> = T | null;
export type Optional<T> = T | undefined;
