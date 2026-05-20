import axios, { AxiosInstance } from "axios";

const API_PREFIX = "/api/v1";

class ApiClient {
  private http: AxiosInstance;

  constructor() {
    this.http = axios.create({ baseURL: API_PREFIX });
    this.http.interceptors.request.use((config) => {
      const token =
        typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      if (token) config.headers.Authorization = `Bearer ${token}`;
      return config;
    });
  }

  async login(email: string, password: string) {
    const form = new URLSearchParams({ username: email, password });
    const { data } = await this.http.post("/auth/login", form);
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    return data;
  }

  listDatasets = (page = 1, size = 50) =>
    this.http.get("/datasets", { params: { page, size } }).then((r) => r.data);

  getDataset = (id: string) => this.http.get(`/datasets/${id}`).then((r) => r.data);

  createJob = (payload: { dataset_id: string; type?: string; params: object }) =>
    this.http.post("/jobs", payload).then((r) => r.data);

  getJob = (id: string) => this.http.get(`/jobs/${id}`).then((r) => r.data);

  reviewQueue = (page = 1, size = 50) =>
    this.http.get("/reviews/queue", { params: { page, size } }).then((r) => r.data);

  submitReview = (
    annotationId: string,
    payload: { decision: string; corrected_payload?: object; notes?: string }
  ) => this.http.post(`/reviews/${annotationId}`, payload).then((r) => r.data);

  createExport = (dataset_id: string, format: string) =>
    this.http.post("/jobs/exports", { dataset_id, format }).then((r) => r.data);

  audit = () => this.http.get("/admin/audit").then((r) => r.data);
}

export const api = new ApiClient();
