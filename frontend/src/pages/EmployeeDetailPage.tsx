import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogClose } from '../components/ui/Dialog';
import { apiClient } from '../utils/api';
import { Employee, EmployeeRole, EmployeeStatus, Task, LeaveRequest, DailyLog } from '../types';
import { useAuthStore } from '../store/auth';
import { formatDate, cn } from '../utils/helpers';
import { ArrowLeft, Edit, Shield, Key, User, Calendar, ClipboardList, FileText, Loader2, Mail, Phone, Building2 } from 'lucide-react';
import { toast } from 'sonner';
import { Link } from 'react-router-dom';

export function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, hasRole } = useAuthStore();
  const isAdminOrAbove = hasRole('admin', 'super_admin');
  const isManagerOrAbove = hasRole('manager', 'admin', 'super_admin');
  const isOwnProfile = user?.id === id;

  const { data: employee, isLoading } = useQuery({
    queryKey: ['employee', id],
    queryFn: () => apiClient.getEmployee(id!),
    enabled: !!id,
  });

  const { data: departmentsData } = useQuery({
    queryKey: ['departments', 'for-employee-edit'],
    queryFn: () => apiClient.getDepartments({ page_size: 100 }),
    enabled: isAdminOrAbove,
  });

  const { data: tasksData } = useQuery({
    queryKey: ['employee-tasks', id],
     queryFn: () => apiClient.getTasks({ assignee_id: id, page_size: 10 }),
    enabled: !!id,
  });

  const { data: leavesData } = useQuery({
    queryKey: ['employee-leaves', id],
    queryFn: () => apiClient.getLeaves({ employee_id: id, page_size: 10 }),
    enabled: !!id && isManagerOrAbove,
  });

  const { data: logsData } = useQuery({
    queryKey: ['employee-logs', id],
    queryFn: () => apiClient.getDailyLogs({ employee_id: id, page_size: 10 }),
    enabled: !!id && (isManagerOrAbove || isOwnProfile),
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Employee>) => apiClient.updateEmployee(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employee', id] });
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      toast.success('Employee updated');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const resetPasswordMutation = useMutation({
    mutationFn: (password: string) => apiClient.adminResetPassword(id!, { password, confirm_password: password }),
    onSuccess: () => toast.success('Password reset successfully'),
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: () => apiClient.deleteEmployee(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      toast.success('Employee deactivated');
      navigate('/employees');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  if (!id) return null;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" onClick={() => navigate('/employees')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <h1 className="text-3xl font-bold tracking-tight">Employee Details</h1>
        </div>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse bg-muted rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (!employee?.data) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" onClick={() => navigate('/employees')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <h1 className="text-3xl font-bold tracking-tight">Employee Details</h1>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <User className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">Employee Not Found</h2>
            <p className="text-muted-foreground mb-4">This employee may have been deleted or you don't have permission to view it.</p>
            <Button onClick={() => navigate('/employees')}>Back to Employees</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const emp = employee.data;
  const canEdit = isAdminOrAbove && emp.id !== user?.id;
  const canResetPassword = isAdminOrAbove && emp.id !== user?.id;
  const canDeactivate = isAdminOrAbove && emp.id !== user?.id;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" onClick={() => navigate('/employees')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold tracking-tight">{emp.first_name} {emp.last_name}</h1>
          <p className="text-muted-foreground">{emp.employee_id} • {emp.department_name || 'No department'}</p>
        </div>
        {canEdit && (
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Edit className="mr-2 h-4 w-4" />
                Edit
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
               <EmployeeEditForm
                 employee={emp}
                 departments={departmentsData?.data.items || []}
                 onSubmit={updateMutation.mutate}
               />
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          {/* Profile Info */}
          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center gap-4">
                <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                  <User className="h-8 w-8 text-primary" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold">{emp.first_name} {emp.last_name}</h2>
                  <p className="text-muted-foreground">{emp.employee_id}</p>
                  <Badge variant={emp.role === 'super_admin' ? 'default' : emp.role === 'admin' ? 'secondary' : 'outline'} className="mt-1">
                    {emp.role === 'super_admin' ? 'Super Admin' : emp.role === 'admin' ? 'Admin' : emp.role === 'manager' ? 'Manager' : 'Employee'}
                  </Badge>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2 pt-4 border-t">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Email</label>
                  <p className="flex items-center gap-2">
                    <Mail className="h-4 w-4 text-muted-foreground" />
                    {emp.email}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Phone</label>
                  <p className="flex items-center gap-2">
                    <Phone className="h-4 w-4 text-muted-foreground" />
                    {emp.phone || 'Not provided'}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Department</label>
                  <p className="flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    {emp.department_name || 'Not assigned'}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Status</label>
                  <Badge variant={emp.status === 'active' ? 'default' : emp.status === 'locked' ? 'destructive' : 'secondary'}>
                    {emp.status}
                  </Badge>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Last Login</label>
                  <p className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    {emp.last_login ? formatDate(emp.last_login) : 'Never'}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Created</label>
                  <p>{formatDate(emp.created_at)}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Tasks Tab */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Assigned Tasks</CardTitle>
                {isManagerOrAbove && (
                  <Button asChild size="sm">
                    <Link to={`/tasks?assigned_to=${emp.id}`}>View All</Link>
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
                {tasksData?.data.items?.length > 0 ? (
                <div className="space-y-3">
                  {tasksData?.data.items?.map((task: Task) => (
                    <Link key={task.id} to={`/tasks/${task.id}`} className="block hover:bg-accent rounded-lg p-3 transition-colors">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="font-medium truncate">{task.title}</p>
                          <p className="text-sm text-muted-foreground truncate">{task.department_name || 'No department'}</p>
                        </div>
                        <Badge variant="status" status={task.status}>{task.status.replace('_', ' ')}</Badge>
                      </div>
                      {task.due_date && (
                        <p className={cn(
                          'text-xs mt-1',
                          task.is_overdue ? 'text-destructive' : 'text-muted-foreground'
                        )}>
                          {task.is_overdue ? 'Overdue' : 'Due'} {formatDate(task.due_date)}
                        </p>
                      )}
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-center py-8 text-muted-foreground">No tasks assigned</p>
              )}
            </CardContent>
          </Card>

          {/* Leave Requests Tab */}
          {isManagerOrAbove && (
            <Card>
              <CardHeader>
                <CardTitle>Leave Requests</CardTitle>
              </CardHeader>
              <CardContent>
                {leavesData?.data.items?.length > 0 ? (
                  <div className="space-y-3">
                    {leavesData?.data.items?.map((leave: LeaveRequest) => (
                      <Link key={leave.id} to={`/leaves/${leave.id}`} className="block hover:bg-accent rounded-lg p-3 transition-colors">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="font-medium capitalize truncate">{leave.leave_type.replace('_', ' ')}</p>
                            <p className="text-sm text-muted-foreground">
                              {formatDate(leave.start_date)} - {formatDate(leave.end_date)} ({leave.duration_days} days)
                            </p>
                          </div>
                          <Badge variant="status" status={leave.status}>{leave.status}</Badge>
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <p className="text-center py-8 text-muted-foreground">No leave requests</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Daily Logs Tab */}
          {(isManagerOrAbove || isOwnProfile) && (
            <Card>
              <CardHeader>
                <CardTitle>Recent Daily Logs</CardTitle>
              </CardHeader>
              <CardContent>
                {logsData?.data.items?.length > 0 ? (
                  <div className="space-y-3">
                    {logsData?.data.items?.map((log: DailyLog) => (
                      <Link key={log.id} to={`/tasks/${log.task_id}`} className="block hover:bg-accent rounded-lg p-3 transition-colors">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="font-medium truncate">{log.task_title || 'No task linked'}</p>
                            <p className="text-sm text-muted-foreground">{formatDate(log.log_date)} • {log.hours_spent ? `${log.hours_spent}h` : 'No hours'}</p>
                          </div>
                          <Badge variant="status" status={log.status}>{log.status.replace('_', ' ')}</Badge>
                        </div>
                        {log.progress_notes && (
                          <p className="text-sm text-muted-foreground mt-1 truncate max-w-xs">{log.progress_notes}</p>
                        )}
                      </Link>
                    ))}
                  </div>
                ) : (
                  <p className="text-center py-8 text-muted-foreground">No daily logs</p>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          {/* Admin Actions */}
          {canEdit && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-4 w-4" />
                  Admin Actions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {canResetPassword && (
                  <Button variant="outline" className="w-full justify-start" onClick={() => {
                    const newPassword = prompt('Enter new password (min 12 chars):');
                    if (newPassword && newPassword.length >= 12) {
                      resetPasswordMutation.mutate(newPassword);
                    } else if (newPassword) {
                      toast.error('Password must be at least 12 characters');
                    }
                  }} disabled={resetPasswordMutation.isPending}>
                    <Key className="mr-2 h-4 w-4" />
                    {resetPasswordMutation.isPending ? 'Resetting...' : 'Reset Password'}
                  </Button>
                )}

                {canDeactivate && (
                  <Button variant="destructive" className="w-full justify-start" onClick={() => {
                    if (confirm(`Are you sure you want to deactivate ${emp.first_name} ${emp.last_name}? This action cannot be undone.`)) {
                      deleteMutation.mutate();
                    }
                  }} disabled={deleteMutation.isPending}>
                    <User className={cn(deleteMutation.isPending && 'animate-spin', 'mr-2 h-4 w-4')} />
                    {deleteMutation.isPending ? 'Deactivating...' : 'Deactivate Employee'}
                  </Button>
                )}
              </CardContent>
            </Card>
          )}

          {/* Quick Stats */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Stats</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                <div className="flex items-center gap-3">
                  <ClipboardList className="h-5 w-5 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Assigned Tasks</span>
                </div>
                <span className="font-semibold">{tasksData?.data.total || 0}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Leave Requests</span>
                </div>
                <span className="font-semibold">{leavesData?.data.total || 0}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                <div className="flex items-center gap-3">
                  <Calendar className="h-5 w-5 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Daily Logs</span>
                </div>
                <span className="font-semibold">{logsData?.data.total || 0}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

interface EmployeeEditFormProps {
  employee: Employee;
  departments: Array<{ id: string; name: string }>;
  onSubmit: (data: Partial<Employee>) => void;
}

function EmployeeEditForm({ employee, departments, onSubmit }: EmployeeEditFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);
    const formData = new FormData(e.currentTarget);
    const departmentId = formData.get('department_id') as string;
    const data = {
      email: formData.get('email') as string,
      first_name: formData.get('first_name') as string,
      last_name: formData.get('last_name') as string,
      phone: formData.get('phone') as string || undefined,
      role: formData.get('role') as EmployeeRole,
      department_id: departmentId === '__none__' ? undefined : departmentId || undefined,
      status: formData.get('status') as EmployeeStatus,
    };
    await onSubmit(data);
    setIsSubmitting(false);
  };

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle>Edit Employee</DialogTitle>
      </DialogHeader>
      <div className="grid gap-4 py-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
            <label htmlFor="first_name" className="text-sm font-medium">First Name *</label>
            <Input id="first_name" name="first_name" required defaultValue={employee.first_name} />
          </div>
          <div className="grid gap-2">
            <label htmlFor="last_name" className="text-sm font-medium">Last Name *</label>
            <Input id="last_name" name="last_name" required defaultValue={employee.last_name} />
          </div>
        </div>
        <div className="grid gap-2">
          <label htmlFor="email" className="text-sm font-medium">Email *</label>
          <Input id="email" name="email" type="email" required defaultValue={employee.email} />
        </div>
        <div className="grid gap-2">
          <label htmlFor="phone" className="text-sm font-medium">Phone</label>
          <Input id="phone" name="phone" type="tel" defaultValue={employee.phone || ''} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
            <label htmlFor="role" className="text-sm font-medium">Role *</label>
            <Select name="role" defaultValue={employee.role} required>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="employee">Employee</SelectItem>
                <SelectItem value="manager">Manager</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
                {employee.role === 'super_admin' && <SelectItem value="super_admin">Super Admin</SelectItem>}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <label htmlFor="status" className="text-sm font-medium">Status *</label>
            <Select name="status" defaultValue={employee.status} required>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="locked">Locked</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="grid gap-2">
          <label htmlFor="department_id" className="text-sm font-medium">Department</label>
          <Select name="department_id" defaultValue={employee.department_id || '__none__'}>
            <SelectTrigger>
              <SelectValue placeholder="Select department" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">No department</SelectItem>
              {departments.map((department) => (
                <SelectItem key={department.id} value={department.id}>{department.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <DialogFooter>
        <DialogClose asChild>
          <Button type="button" variant="outline">Cancel</Button>
        </DialogClose>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Update Employee
        </Button>
      </DialogFooter>
    </form>
  );
}
