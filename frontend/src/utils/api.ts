import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios';
import { getAuthStore } from '../store/auth';

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

export interface EmployeeCreateInput {
  employee_id?: string;
  email: string;
  first_name: string;
  last_name: string;
  phone?: string;
  department_id?: string;
  role?: string;
  status?: string;
  password: string;
  confirm_password: string;
}

export interface TaskCreateInput {
  title: string;
  description?: string;
  department_id?: string;
  assigned_to_id?: string;
  priority?: string;
  due_date?: string;
  estimated_hours?: number;
  sort_order?: number;
}

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_URL}/api/v1`,
      withCredentials: true, // Important for cookie-based auth
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // Add request ID for tracing
        config.headers['X-Request-ID'] = crypto.randomUUID();
        if (config.params && typeof config.params === 'object' && !Array.isArray(config.params)) {
          config.params = Object.fromEntries(
            Object.entries(config.params).filter(([, value]) => value !== '' && value !== undefined && value !== null)
          );
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config;

        // Handle 401 - session expired
        if (error.response?.status === 401 && originalRequest && !originalRequest.url?.includes('/auth/login')) {
          const authStore = getAuthStore();
          authStore.logout();
          window.location.href = '/login';
          return Promise.reject(error);
        }

        // Handle 403 - forbidden
        if (error.response?.status === 403) {
          console.error('Access denied:', error.response.data);
        }

        // Handle 429 - rate limited
        if (error.response?.status === 429) {
          const retryAfter = error.response.headers['retry-after'];
          console.warn(`Rate limited. Retry after ${retryAfter} seconds`);
        }

        return Promise.reject(error);
      }
    );
  }

  get instance(): AxiosInstance {
    return this.client;
  }

  async get<T = unknown>(url: string, config?: AxiosRequestConfig) {
    return this.client.get<T>(url, config);
  }

  // Auth endpoints
  async login(data: { employee_id: string; password: string; remember_me: boolean }) {
    return this.client.post('/auth/login', data);
  }

  async logout(revokeAll = false) {
    return this.client.post('/auth/logout', undefined, { params: { revoke_all: revokeAll } });
  }

  async refresh() {
    return this.client.post('/auth/refresh');
  }

  async getProfile() {
    return this.client.get('/auth/me');
  }

  async getSessions() {
    return this.client.get('/auth/sessions');
  }

  async registerCompany(data: {
    company_name: string;
    company_slug: string;
    admin_email: string;
    admin_password: string;
    admin_first_name: string;
    admin_last_name: string;
    admin_phone?: string;
  }) {
    return this.client.post('/auth/register', data);
  }

  async forgotPassword(data: { employee_id: string; email: string }) {
    return this.client.post('/auth/forgot-password', data);
  }

  async resetPassword(data: { token: string; password: string; confirm_password: string }) {
    return this.client.post('/auth/reset-password', data);
  }

  async changePassword(data: { current_password: string; new_password: string; confirm_password: string }) {
    return this.client.post('/auth/change-password', data);
  }

  async adminResetPassword(employeeId: string, data: { password: string; confirm_password: string }) {
    return this.client.post(`/employees/${employeeId}/reset-password`, data);
  }

  async revokeSession(sessionId: string) {
    return this.client.post(`/auth/sessions/${sessionId}/revoke`);
  }

  async revokeAllSessions() {
    return this.client.post('/auth/sessions/revoke-all');
  }

  // Company endpoints
  async getCompany() {
    return this.client.get('/company/me');
  }

  async updateCompany(data: Partial<{ name: string; email: string; phone: string; address: string }>) {
    return this.client.patch('/company/me', data);
  }

  // Department endpoints
  async getDepartments(params?: { parent_id?: string; search?: string; root_only?: boolean; page?: number; page_size?: number }) {
    return this.client.get('/departments', { params });
  }

  async getDepartmentTree() {
    return this.client.get('/departments/tree');
  }

  async getDepartment(id: string) {
    return this.client.get(`/departments/${id}`);
  }

  async createDepartment(data: { name: string; description?: string | null; parent_id?: string | null; sort_order?: number }) {
    return this.client.post('/departments', data);
  }

  async updateDepartment(id: string, data: Partial<{ name: string; description: string | null; parent_id: string | null; sort_order: number }>) {
    return this.client.patch(`/departments/${id}`, data);
  }

  async deleteDepartment(id: string, reassignTo?: string) {
    return this.client.delete(`/departments/${id}`, { params: { reassign_to: reassignTo } });
  }

  // Employee endpoints
  async getEmployees(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    department_id?: string;
    role?: string;
    status?: string;
  }) {
    return this.client.get('/employees', { params });
  }

  async getEmployeeSummaries() {
    return this.client.get('/employees/summary');
  }

  async getEmployee(id: string) {
    return this.client.get(`/employees/${id}`);
  }

  async createEmployee(data: EmployeeCreateInput) {
    return this.client.post('/employees', data);
  }

  async updateEmployee(id: string, data: Partial<{
    email: string;
    first_name: string;
    last_name: string;
    phone: string | null;
    department_id: string | null;
    role: string;
    status: string;
  }>) {
    return this.client.patch(`/employees/${id}`, data);
  }

  async resetEmployeePassword(id: string, data: { password: string; confirm_password: string }) {
    return this.client.post(`/employees/${id}/reset-password`, data);
  }

  async deleteEmployee(id: string) {
    return this.deactivateEmployee(id);
  }

  async deactivateEmployee(id: string) {
    return this.client.delete(`/employees/${id}`);
  }

  // Task endpoints
  async getTasks(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    department_id?: string;
    assignee_id?: string;
    priority?: string;
    search?: string;
  }) {
    return this.client.get('/tasks', { params });
  }

  async getMyTasks(status?: string) {
    return this.client.get('/tasks/my', { params: { status } });
  }

  async getDepartmentTasks(departmentId: string, status?: string) {
    return this.client.get(`/tasks/department/${departmentId}`, { params: { status } });
  }

  async getTask(id: string) {
    return this.client.get(`/tasks/${id}`);
  }

  async createTask(data: {
    title: string;
    description?: string;
    department_id?: string;
    assigned_to_id?: string;
    priority?: string;
    due_date?: string;
    estimated_hours?: number;
    sort_order?: number;
  }) {
    return this.client.post('/tasks', data);
  }

  async updateTask(id: string, data: Partial<{
    title: string;
    description: string | null;
    department_id: string | null;
    priority: string;
    due_date: string | null;
    estimated_hours: number | null;
    sort_order: number;
  }>) {
    return this.client.patch(`/tasks/${id}`, data);
  }

  async assignTask(id: string, assignedToId: string) {
    return this.client.post(`/tasks/${id}/assign`, { assigned_to_id: assignedToId });
  }

  async updateTaskStatus(id: string, status: string) {
    return this.client.post(`/tasks/${id}/status`, { status });
  }

  async deleteTask(id: string) {
    return this.client.delete(`/tasks/${id}`);
  }

  // Daily Log endpoints
  async getDailyLogs(params?: {
    page?: number;
    page_size?: number;
    employee_id?: string;
    task_id?: string;
    start_date?: string;
    end_date?: string;
    status?: string;
  }) {
    return this.client.get('/daily-logs', { params });
  }

  async getMyDailySummary(startDate: string, endDate: string) {
    return this.client.get('/daily-logs/my/summary', { params: { start_date: startDate, end_date: endDate } });
  }

  async getDepartmentDailySummary(departmentId: string, logDate: string) {
    return this.client.get(`/daily-logs/department/${departmentId}/summary`, { params: { log_date: logDate } });
  }

  async getDailyLog(id: string) {
    return this.client.get(`/daily-logs/${id}`);
  }

  async createDailyLog(data: {
    task_id?: string | null;
    log_date: string;
    hours_spent?: number;
    progress_notes?: string;
    status?: string;
  }) {
    return this.client.post('/daily-logs', data);
  }

  async updateDailyLog(id: string, data: Partial<{
    task_id: string | null;
    hours_spent: number | null;
    progress_notes: string | null;
    status: string;
  }>) {
    return this.client.patch(`/daily-logs/${id}`, data);
  }

  async deleteDailyLog(id: string) {
    return this.client.delete(`/daily-logs/${id}`);
  }

  // Leave endpoints
  async getLeaves(params?: {
    page?: number;
    page_size?: number;
    employee_id?: string;
    status?: string;
    leave_type?: string;
    start_date?: string;
    end_date?: string;
  }) {
    return this.client.get('/leaves', { params });
  }

  async getLeaveBalance(year?: number) {
    return this.client.get('/leaves/balance', { params: { year } });
  }

  async getLeave(id: string) {
    return this.client.get(`/leaves/${id}`);
  }

  async createLeave(data: {
    leave_type: string;
    start_date: string;
    end_date: string;
    reason?: string;
  }) {
    return this.client.post('/leaves', data);
  }

  async updateLeave(id: string, data: Partial<{
    leave_type: string;
    start_date: string;
    end_date: string;
    reason: string | null;
    status: string;
    review_notes: string;
  }>) {
    return this.client.patch(`/leaves/${id}`, data);
  }

  async reviewLeave(id: string, data: { status: string; review_notes?: string }) {
    return this.client.post(`/leaves/${id}/review`, data);
  }

  async cancelLeave(id: string) {
    return this.client.post(`/leaves/${id}/cancel`);
  }

  async deleteLeave(id: string) {
    return this.client.delete(`/leaves/${id}`);
  }

  // Audit endpoints
  async getAuditLogs(params?: {
    page?: number;
    page_size?: number;
    company_id?: string;
    employee_id?: string;
    action?: string;
    resource_type?: string;
    resource_id?: string;
    start_date?: string;
    end_date?: string;
  }) {
    return this.client.get('/audit', { params });
  }

  async getAuditActions() {
    return this.client.get('/audit/actions');
  }

  async getAuditResourceTypes() {
    return this.client.get('/audit/resource-types');
  }

  async verifyAuditIntegrity() {
    return this.client.get('/audit/verify-integrity');
  }

  async exportAuditLogs(params?: { company_id?: string; start_date?: string; end_date?: string }) {
    return this.client.get('/audit/export', { params, responseType: 'blob' });
  }

  // Team endpoints (manager+)
  async getTeamMembers(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    status?: string;
  }) {
    return this.client.get('/employees/team', { params });
  }

  async getTeamSummary() {
    return this.client.get('/employees/team/summary');
  }

  // Profile endpoints
  async updateProfile(data: Partial<{ first_name: string; last_name: string; phone: string | null }>) {
    return this.client.patch('/auth/me', data);
  }

  async deleteMyAccount() {
    return this.client.delete('/auth/me');
  }

  async exportMyData() {
    return this.client.get('/auth/me/export');
  }

  // Analytics endpoints (admin+)
  async getAnalytics(range: string) {
    return this.client.get('/analytics', { params: { range } });
  }
}

export const api = new ApiClient().instance;
export const apiClient = new ApiClient();
