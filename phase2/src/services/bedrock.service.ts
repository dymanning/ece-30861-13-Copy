import { BedrockRuntimeClient, InvokeModelCommand } from '@aws-sdk/client-bedrock-runtime';

const region = process.env.BEDROCK_REGION || 'us-east-1';
const modelId = process.env.BEDROCK_MODEL_ID || 'amazon.titan-text-lite-v1';

const client = new BedrockRuntimeClient({ region });

async function invokeBedrockJSON(prompt: string): Promise<any> {
  const body = JSON.stringify({
    inputText: prompt,
    textGenerationConfig: { maxTokenCount: 1024, temperature: 0.2, topP: 0.9 },
  });
  const cmd = new InvokeModelCommand({ modelId, contentType: 'application/json', accept: 'application/json', body });
  const res = await client.send(cmd);
  const txt = typeof res.body === 'string' ? res.body : new TextDecoder().decode(res.body as any);
  try {
    return JSON.parse(txt);
  } catch {
    return { error: 'Malformed JSON from Bedrock', raw: txt };
  }
}

export async function summarizePerformanceClaims(input: { name: string; readme?: string; metrics?: any }): Promise<{ performance_claims?: number; notes?: string }> {
  const prompt = `You are scoring ML model performance claims conservatively.\nName: ${input.name}\nREADME: ${input.readme || ''}\nKnown metrics: ${JSON.stringify(input.metrics || {})}\nReturn strict JSON with keys: performance_claims (number 0..1, lower-is-better), notes (string). Never invent data.`;
  const out = await invokeBedrockJSON(prompt);
  return typeof out === 'object' ? out : { performance_claims: 0.0, notes: 'bedrock_error' };
}

export async function assessCodeQuality(input: { name: string; repoUrl?: string; signals?: any }): Promise<{ code_quality?: number; reviewedness?: number; notes?: string }> {
  const prompt = `Assess code quality and reviewedness conservatively.\nName: ${input.name}\nRepo: ${input.repoUrl || ''}\nSignals: ${JSON.stringify(input.signals || {})}\nReturn JSON: { code_quality: 0..1, reviewedness: 0..1, notes: string }. Avoid hallucinations.`;
  const out = await invokeBedrockJSON(prompt);
  return typeof out === 'object' ? out : { code_quality: 0.0, reviewedness: 0.0, notes: 'bedrock_error' };
}

export async function assessDatasetQuality(input: { name: string; datasetCard?: string; signals?: any }): Promise<{ dataset_quality?: number; notes?: string }> {
  const prompt = `Assess dataset quality conservatively.\nName: ${input.name}\nCard: ${input.datasetCard || ''}\nSignals: ${JSON.stringify(input.signals || {})}\nReturn JSON: { dataset_quality: 0..1, notes: string }.`;
  const out = await invokeBedrockJSON(prompt);
  return typeof out === 'object' ? out : { dataset_quality: 0.0, notes: 'bedrock_error' };
}
