import axios, { AxiosInstance, AxiosError } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for API key
api.interceptors.request.use((config) => {
  const apiKey = process.env.NEXT_PUBLIC_API_KEY;
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey;
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 429) {
      console.error('Rate limit exceeded');
    }
    return Promise.reject(error);
  }
);

// API Types
export interface APIResponse<T> {
  status: 'success' | 'error' | 'warning';
  data?: T;
  message?: string | null;
  errors?: Array<{
    code: string;
    message: string;
    field?: string | null;
  }> | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// Property Types
export interface PropertySearchParams {
  query?: string;
  parcel_id?: string;
  city?: string;
  subdivision?: string;
  min_value?: number;
  max_value?: number;
  only_appeal_candidates?: boolean;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface PropertySearchResponse {
  properties: PropertySummary[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_more: boolean;
}

export interface PropertySummary {
  id: string;
  parcel_id: string;
  address: string;
  city: string | null;
  state?: string;
  zip_code?: string | null;
  county?: string;
  owner_name: string | null;
  total_value: number | null;
  assessed_value: number | null;
  property_type: string | null;
  subdivision?: string | null;
  is_appeal_candidate?: boolean;
}

export interface PropertyDetail extends PropertySummary {
  owner_address?: string | null;
  land_value?: number | null;
  improvement_value?: number | null;
  neighborhood_code?: string | null;
  legal_description?: string | null;
  tax_area_acres?: number | null;
  tax_district?: string | null;
  mill_rate?: number;
  estimated_annual_tax?: number | null;
  source_date?: string | null;
  last_updated?: string | null;
  fairness_score?: number | null;
  recommended_action?: string | null;
  estimated_savings?: number | null;
  last_analyzed?: string | null;
}

export interface AddressSuggestion {
  property_id: string;
  parcel_id: string;
  address: string;
  city: string | null;
  match_score: number;
}

// Analysis Types
export interface AnalysisResult {
  id: string;
  property_id: string;
  fairness_score: number;
  confidence_level: number;
  recommended_action: 'APPEAL' | 'MONITOR' | 'NONE';
  fair_assessed_value: number;
  estimated_savings: number;
  comparable_count: number;
  analysis_date: string;
}

export interface AnalyzeOptions {
  force_refresh?: boolean;
  include_comparables?: boolean;
}

// Appeal Types
export interface AppealPackage {
  appeal_id: string | null;
  property_id: string;
  parcel_id: string;
  address: string | null;
  owner_name: string | null;
  current_assessed_value: number | null;
  requested_assessed_value: number | null;
  estimated_annual_savings: number | null;
  appeal_letter: string;
  executive_summary: string | null;
  evidence_summary: string | null;
  fairness_score: number;
  confidence_level: number;
  comparable_count: number;
  jurisdiction: string;
  filing_deadline: string | null;
  required_forms: string[];
  statute_reference: string;
  generated_at: string;
  generator_type: string;
  template_style: string;
  word_count: number;
  status: string;
}

export interface AppealListItem {
  appeal_id: string;
  property_id: string;
  parcel_id: string;
  address: string | null;
  status: string;
  estimated_savings: number | null;
  generated_at: string;
}

// Portfolio Types
export interface PortfolioSummary {
  id: string;
  name: string;
  property_count: number;
  total_value: number;
  created_at: string;
}

export interface PortfolioDetail extends PortfolioSummary {
  properties: PropertySummary[];
  total_potential_savings: number;
}

export interface TopProperty {
  parcel_id: string;
  address: string;
  potential_savings: number;
  fairness_score: number;
}

export interface DashboardData {
  portfolio_id: string;
  portfolio_name: string;
  metrics: {
    total_properties: number;
    total_market_value: number;
    total_assessed_value: number;
    estimated_annual_tax: number;
    total_potential_savings: number;
    appeal_candidates: number;
    average_fairness_score: number;
  };
  top_savings_opportunities: TopProperty[];
  appeal_deadline: string;
  days_until_deadline: number;
}

// Property API
export const propertyApi = {
  search: async (params: PropertySearchParams) => {
    const response = await api.post<PropertySearchResponse>('/properties/search', params);
    return response.data;
  },

  getById: async (id: string) => {
    const response = await api.get<APIResponse<PropertyDetail>>(`/properties/${id}`);
    return response.data;
  },

  autocomplete: async (query: string) => {
    const response = await api.get<AddressSuggestion[]>('/properties/autocomplete/address', {
      params: { q: query }
    });
    return response.data;
  }
};

// Analysis API
export const analysisApi = {
  analyze: async (propertyId: string, options?: AnalyzeOptions) => {
    const response = await api.post<APIResponse<AnalysisResult>>('/analysis/assess', {
      property_id: propertyId,
      ...options
    });
    return response.data;
  },

  getHistory: async (propertyId: string) => {
    const response = await api.get<APIResponse<AnalysisResult[]>>(`/analysis/history/${propertyId}`);
    return response.data;
  }
};

// Appeal API
export const appealApi = {
  generate: async (propertyId: string, style: string = 'formal') => {
    const response = await api.post<APIResponse<AppealPackage>>('/appeals/generate', {
      property_id: propertyId,
      style
    });
    return response.data;
  },

  downloadPdf: async (propertyId: string) => {
    const response = await api.post(`/appeals/generate/${propertyId}/pdf`, null, {
      responseType: 'blob'
    });
    return response.data;
  },

  list: async (status?: string) => {
    const response = await api.get<APIResponse<AppealListItem[]>>('/appeals/list', {
      params: { status }
    });
    return response.data;
  },

  get: async (appealId: string) => {
    const response = await api.get<APIResponse<AppealPackage>>(`/appeals/${appealId}`);
    return response.data;
  },

  delete: async (appealId: string) => {
    const response = await api.delete(`/appeals/${appealId}`);
    return response.data;
  },

  updateStatus: async (appealId: string, status: string) => {
    const response = await api.patch<APIResponse<AppealListItem>>(`/appeals/${appealId}/status`, null, {
      params: { status }
    });
    return response.data;
  }
};

// Portfolio API
export const portfolioApi = {
  list: async (userId: string) => {
    const response = await api.get<APIResponse<PortfolioSummary[]>>('/portfolios', {
      params: { user_id: userId }
    });
    return response.data;
  },

  get: async (portfolioId: string) => {
    const response = await api.get<APIResponse<PortfolioDetail>>(`/portfolios/${portfolioId}`);
    return response.data;
  },

  create: async (data: { name: string; description?: string; user_id: string }) => {
    const response = await api.post<APIResponse<PortfolioSummary>>('/portfolios', data);
    return response.data;
  },

  delete: async (portfolioId: string) => {
    const response = await api.delete(`/portfolios/${portfolioId}`);
    return response.data;
  },

  getDashboard: async (portfolioId: string) => {
    const response = await api.get<APIResponse<DashboardData>>(`/portfolios/${portfolioId}/dashboard`);
    return response.data;
  },

  addProperty: async (portfolioId: string, parcelId: string) => {
    const response = await api.post(`/portfolios/${portfolioId}/properties`, {
      parcel_id: parcelId
    });
    return response.data;
  },

  removeProperty: async (portfolioId: string, propertyId: string) => {
    const response = await api.delete(`/portfolios/${portfolioId}/properties/${propertyId}`);
    return response.data;
  },

  analyzeAll: async (portfolioId: string) => {
    const response = await api.post<APIResponse<{ analyzed: number; failed: number }>>(`/portfolios/${portfolioId}/analyze`);
    return response.data;
  },

  exportCsv: async (portfolioId: string) => {
    const response = await api.get(`/portfolios/${portfolioId}/export`, {
      params: { format: 'csv' },
      responseType: 'blob'
    });
    return response.data;
  },

  importCsv: async (portfolioId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post(`/portfolios/${portfolioId}/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  }
};

// Report Types
export interface ReportConfig {
  portfolio_id?: string;
  property_id?: string;
  report_type?: 'portfolio_summary' | 'appeal_package' | 'property_analysis' | 'comparables';
  format?: 'pdf' | 'csv' | 'xlsx' | 'json';
  include_executive_summary?: boolean;
  include_property_details?: boolean;
  include_analysis_results?: boolean;
  include_recommendations?: boolean;
  include_comparables?: boolean;
  only_appeal_candidates?: boolean;
}

export interface ReportMetadata {
  filename: string;
  format: string;
  size_bytes: number;
  generated_at: string;
  properties_included: number;
  total_value?: number;
  total_savings?: number;
}

export interface GeneratedReport {
  id: string;
  name: string;
  type: string;
  format: string;
  created_at: string;
  file_url?: string;
}

// Report API
export const reportApi = {
  generate: async (config: ReportConfig) => {
    const response = await api.post<ReportMetadata>('/reports/generate', config);
    return response.data;
  },

  list: async () => {
    const response = await api.get<APIResponse<GeneratedReport[]>>('/reports');
    return response.data;
  },

  download: async (filename: string) => {
    const response = await api.get(`/reports/download/${filename}`, {
      responseType: 'blob'
    });
    return response.data;
  },

  delete: async (reportId: string) => {
    const response = await api.delete(`/reports/${reportId}`);
    return response.data;
  },

  // Portfolio-specific quick reports
  portfolioPdf: async (portfolioId: string, onlyAppealCandidates: boolean = false) => {
    const response = await api.post(`/reports/portfolio/${portfolioId}/pdf`, null, {
      params: { only_appeal_candidates: onlyAppealCandidates },
      responseType: 'blob'
    });
    return response.data;
  },

  portfolioCsv: async (portfolioId: string, includeAnalysis: boolean = true) => {
    const response = await api.post(`/reports/portfolio/${portfolioId}/csv`, null, {
      params: { include_analysis: includeAnalysis },
      responseType: 'blob'
    });
    return response.data;
  },

  portfolioExcel: async (portfolioId: string) => {
    const response = await api.post(`/reports/portfolio/${portfolioId}/excel`, null, {
      responseType: 'blob'
    });
    return response.data;
  },

  // Single property analysis report
  propertyAnalysis: async (propertyId: string, format: 'pdf' | 'csv' | 'json' = 'json') => {
    const response = await api.post(`/reports/property/${propertyId}/analysis`, null, {
      params: { format },
      responseType: format === 'json' ? 'json' : 'blob'
    });
    return response.data;
  }
};
