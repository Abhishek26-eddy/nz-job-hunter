import axios from "axios";

const isBrowser = typeof window !== "undefined";
const baseURL = isBrowser
  ? "/api"
  : process.env.NEXT_PUBLIC_API_URL || "http://backend:8000/api";

export const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Job {
  id: number;
  title: string;
  company?: { name: string };
  location?: string;
  workplace_type?: string;
  match_score?: number;
  match_reason?: string;
  missing_skills?: string[];
  visa_sponsorship_inferred: string;
  salary_estimate?: string;
  should_apply?: boolean;
  application_url?: string;
  description?: string;
  created_at: string;
  role_category?: string;
  role_priority?: string;
  critical_missing_skills?: string[];
  score_breakdown?: Record<string, number>;
  application_status?: string | null;
}

export interface Company {
  id: number;
  name: string;
  slug: string;
  city?: string;
  country?: { name: string };
  industry?: string;
  visa_sponsorship: string;
}

export interface AnalyticsSummary {
  total_jobs: number;
  total_companies: number;
  total_applications: number;
  status_counts: Record<string, number>;
  top_countries: { country: string; jobs: number }[];
}

export async function getJobs(params?: Record<string, any>): Promise<PaginatedResponse<Job>> {
  const clean: Record<string, any> = {};
  for (const [key, value] of Object.entries(params || {})) {
    if (value !== undefined && value !== null && value !== "") {
      clean[key] = value;
    }
  }
  const { data } = await api.get("/v1/jobs", { params: clean });
  return data;
}

export async function getCompanies(
  params?: Record<string, any>
): Promise<PaginatedResponse<Company>> {
  const { data } = await api.get("/v1/companies", { params });
  return data;
}

export async function getAnalytics(): Promise<AnalyticsSummary> {
  const { data } = await api.get("/v1/analytics/summary");
  return data;
}

export async function triggerCrawl(limit = 50): Promise<{ status: string; result: any }> {
  const { data } = await api.post("/v1/crawler/run", null, { params: { limit } });
  return data;
}

export async function matchJob(jobId: number): Promise<any> {
  const { data } = await api.post(`/v1/jobs/${jobId}/match`);
  return data;
}

export interface ResumeRead {
  id: number;
  name: string;
  is_master: boolean;
  content_text?: string;
  file_name?: string;
  created_at: string;
  updated_at: string;
}

export async function listResumes(): Promise<ResumeRead[]> {
  const { data } = await api.get("/v1/resumes");
  return data;
}

export async function uploadResume(file: File): Promise<any> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/v1/resumes/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    params: { is_master: true },
  });
  return data;
}

export interface ApplicationCreate {
  job_id: number;
  status?: string;
  notes?: string;
}

export interface ApplicationRead {
  id: number;
  job_id: number;
  user_id: number;
  status: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export async function createApplication(payload: ApplicationCreate): Promise<ApplicationRead> {
  const { data } = await api.post("/v1/applications", payload);
  return data;
}

export async function runMatching(job_ids?: number[], top_n?: number): Promise<{ status: string; embeddings_generated: number; jobs_scored: number; jobs_reasoned: number }> {
  const { data } = await api.post("/v1/ai/match", { job_ids, top_n });
  return data;
}
