/** Shared TypeScript types matching backend schemas */

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface EmployeeProfile {
  id: string;
  employee_id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string | null;
  role: EmployeeRole;
  status: EmployeeStatus;
  department_id: string | null;
  department_name: string | null;
  company_id: string;
  company_slug: string;
  last_login: string | null;
  created_at: string;
  updated_at: string;
}

export type EmployeeRole = 'employee' | 'manager' | 'admin' | 'super_admin';
export type EmployeeStatus = 'active' | 'inactive' | 'locked' | 'pending';

export interface Employee {
  id: string;
  employee_id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string | null;
  role: EmployeeRole;
  status: EmployeeStatus;
  department_id: string | null;
  department_name: string | null;
  company_id: string;
  company_slug: string;
  last_login: string | null;
  failed_login_attempts: number;
  locked_until: string | null;
  created_at: string;
  updated_at: string;
  task_count?: number;
}

export interface EmployeeSummary {
  id: string;
  employee_id: string;
  full_name: string;
  email: string;
  role: EmployeeRole;
  department_id: string | null;
  department_name: string | null;
}

export interface Company {
  id: string;
  name: string;
  slug: string;
  email: string;
  phone: string | null;
  address: string | null;
  subscription_tier: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Department {
  id: string;
  company_id: string;
  name: string;
  description: string | null;
  parent_id: string | null;
  sort_order: number;
  full_path: string;
  children_count: number;
  employees_count: number;
  created_at: string;
  updated_at: string;
  children?: Department[];
}

export type TaskStatus = 'pending' | 'in_progress' | 'in_review' | 'completed' | 'blocked' | 'cancelled';
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent';

export interface Task {
  id: string;
  company_id: string;
  department_id: string | null;
  assigned_to_id: string | null;
  assigned_to_name: string | null;
  created_by_id: string;
  created_by_name: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string | null;
  completed_at: string | null;
  estimated_hours: number | null;
  actual_hours: number;
  sort_order: number;
  is_overdue: boolean;
  department_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskSummary {
  id: string;
  title: string;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string | null;
  assigned_to_name: string | null;
  department_name: string | null;
  is_overdue: boolean;
}

export type DailyLogStatus = 'not_started' | 'in_progress' | 'completed' | 'blocked' | 'on_hold';

export interface DailyLog {
  id: string;
  employee_id: string;
  employee_name: string;
  task_id: string | null;
  task_title: string | null;
  log_date: string;
  hours_spent: number | null;
  progress_notes: string | null;
  status: DailyLogStatus;
  created_at: string;
  updated_at: string;
}

export interface DailyLogSummary {
  date: string;
  total_hours: number;
  tasks_count: number;
  completed_tasks: number;
  in_progress_tasks: number;
}

export interface DepartmentDailySummary {
  date: string;
  department_id: string;
  department_name: string;
  total_employees: number;
  active_employees: number;
  total_hours: number;
  tasks_completed: number;
  tasks_in_progress: number;
  employee_summaries: DailyLogSummary[];
}

export type LeaveType = 'sick' | 'vacation' | 'personal' | 'emergency' | 'maternity' | 'paternity' | 'bereavement' | 'unpaid' | 'other';
export type LeaveStatus = 'pending' | 'approved' | 'rejected' | 'cancelled' | 'expired';

export interface LeaveRequest {
  id: string;
  employee_id: string;
  employee_name: string;
  employee_email: string;
  department_name: string | null;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  reason: string | null;
  status: LeaveStatus;
  duration_days: number;
  reviewed_by_id: string | null;
  reviewed_by_name: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  is_active: boolean;
  is_upcoming: boolean;
  is_past: boolean;
  created_at: string;
  updated_at: string;
}

export interface LeaveBalance {
  leave_type: LeaveType;
  allocated: number;
  used: number;
  pending: number;
  remaining: number;
}

export interface LeaveBalanceResponse {
  employee_id: string;
  employee_name: string;
  balances: LeaveBalance[];
  year: number;
}

export interface AuditLog {
  id: string;
  company_id: string | null;
  employee_id: string | null;
  employee_name?: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  user_agent: string | null;
  metadata: Record<string, unknown>;
  previous_hash: string | null;
  current_hash: string;
  created_at: string;
}

export interface SessionInfo {
  id: string;
  device_fingerprint: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  last_activity: string;
  expires_at: string;
  is_current: boolean;
}

export interface LoginRequest {
  employee_id: string;
  password: string;
  remember_me: boolean;
}

export interface LoginResponse {
  success: boolean;
  employee: EmployeeProfile;
  message?: string;
}

export interface RegisterCompanyRequest {
  company_name: string;
  company_slug: string;
  admin_email: string;
  admin_password: string;
  admin_first_name: string;
  admin_last_name: string;
  admin_phone?: string;
}

export interface ApiError {
  code: number;
  message: string;
  details?: unknown;
  request_id?: string;
}
