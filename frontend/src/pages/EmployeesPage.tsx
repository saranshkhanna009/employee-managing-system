import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select';
import { Card, CardContent } from '../components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table';
import { Badge } from '../components/ui/Badge';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '../components/ui/DropdownMenu';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogClose } from '../components/ui/Dialog';
import { apiClient } from '../utils/api';
import { Employee, EmployeeRole, EmployeeStatus } from '../types';
import { useAuthStore } from '../store/auth';
import { formatDate } from '../utils/helpers';
import { Plus, Search, MoreVertical, Edit, Trash2, Loader2, Key } from 'lucide-react';
import { toast } from 'sonner';
import { EmployeeCreateInput } from '../utils/api';

export function EmployeesPage() {
  const queryClient = useQueryClient();
  const { user, hasRole } = useAuthStore();
  const isAdminOrAbove = hasRole('admin', 'super_admin');
  const navigate = useNavigate();

  const [filters, setFilters] = useState({
    search: '',
    role: '',
    status: '',
    department_id: '',
    page: 1,
    page_size: 20,
  });

  const { data: employeesData, isLoading } = useQuery({
    queryKey: ['employees', filters],
    queryFn: () => apiClient.getEmployees(filters),
  });

  const { data: departments } = useQuery({
    queryKey: ['departments'],
    queryFn: () => apiClient.getDepartments(),
    select: (res) => res.data.items,
  });

  const createMutation = useMutation({
    mutationFn: (data: EmployeeCreateInput) => apiClient.createEmployee(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      toast.success('Employee created successfully');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteEmployee(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      toast.success('Employee deactivated');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const resetPasswordMutation = useMutation({
    mutationFn: ({ id, password }: { id: string; password: string }) => apiClient.adminResetPassword(id, { password, confirm_password: password }),
    onSuccess: () => toast.success('Password reset successfully'),
    onError: (err: Error) => toast.error(err.message),
  });

  const employees = employeesData?.data.items || [];
  const total = employeesData?.data.total || 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Employees</h1>
          <p className="text-muted-foreground">Manage company employees</p>
        </div>
        {isAdminOrAbove && (
          <Dialog>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Add Employee
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
              <EmployeeForm onSubmit={createMutation.mutate} departments={departments || []} />
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search employees..."
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value, page: 1 })}
                className="pl-10"
              />
            </div>
            <Select value={filters.role} onValueChange={(value) => setFilters({ ...filters, role: value === '__all__' ? '' : value, page: 1 })}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Roles" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All Roles</SelectItem>
                <SelectItem value="employee">Employee</SelectItem>
                <SelectItem value="manager">Manager</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filters.status} onValueChange={(value) => setFilters({ ...filters, status: value === '__all__' ? '' : value, page: 1 })}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All Statuses</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="locked">Locked</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filters.department_id} onValueChange={(value) => setFilters({ ...filters, department_id: value === '__all__' ? '' : value, page: 1 })}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="All Departments" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All Departments</SelectItem>
                {departments?.map((dept: { id: string; name: string }) => (
                  <SelectItem key={dept.id} value={dept.id}>{dept.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Employees Table */}
      <Card>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-12 animate-pulse bg-muted rounded" />
              ))}
            </div>
          ) : (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Employee</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Department</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Last Login</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {employees.length > 0 ? (
                      employees.map((emp: Employee) => (
                        <TableRow key={emp.id}>
                          <TableCell>
                            <Link to={`/employees/${emp.id}`} className="font-medium hover:underline">
                              {emp.first_name} {emp.last_name}
                            </Link>
                            <p className="text-sm text-muted-foreground">{emp.employee_id}</p>
                          </TableCell>
                          <TableCell>
                            <Badge variant={emp.role === 'super_admin' ? 'default' : emp.role === 'admin' ? 'secondary' : 'outline'}>
                              {emp.role === 'super_admin' ? 'Super Admin' : emp.role === 'admin' ? 'Admin' : emp.role === 'manager' ? 'Manager' : 'Employee'}
                            </Badge>
                          </TableCell>
                          <TableCell>{emp.department_name || 'Not assigned'}</TableCell>
                          <TableCell>
                            <Badge variant={emp.status === 'active' ? 'default' : emp.status === 'locked' ? 'destructive' : 'secondary'}>
                              {emp.status}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {emp.last_login ? formatDate(emp.last_login) : <span className="text-muted-foreground">Never</span>}
                          </TableCell>
                          <TableCell className="text-right">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon">
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem asChild>
                                  <Link to={`/employees/${emp.id}`}>View Details</Link>
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                {isAdminOrAbove && emp.id !== user?.id && (
                                  <>
                                    <DropdownMenuItem onClick={() => navigate(`/employees/${emp.id}`)}>
                                      <Edit className="mr-2 h-4 w-4" />
                                      Edit
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => {
                                      const newPassword = prompt('Enter new password (min 12 chars):');
                                      if (newPassword && newPassword.length >= 12) {
                                        resetPasswordMutation.mutate({ id: emp.id, password: newPassword });
                                      } else if (newPassword) {
                                        toast.error('Password must be at least 12 characters');
                                      }
                                    }}>
                                      <Key className="mr-2 h-4 w-4" />
                                      Reset Password
                                    </DropdownMenuItem>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem
                                      onClick={() => {
                                        if (confirm(`Are you sure you want to deactivate ${emp.first_name} ${emp.last_name}?`)) {
                                          deleteMutation.mutate(emp.id);
                                        }
                                      }}
                                      className="text-destructive focus:text-destructive"
                                    >
                                      <Trash2 className="mr-2 h-4 w-4" />
                                      Deactivate
                                    </DropdownMenuItem>
                                  </>
                                )}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                          No employees found
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {total > filters.page_size && (
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-muted-foreground">
                    Showing {(filters.page - 1) * filters.page_size + 1} to{' '}
                    {Math.min(filters.page * filters.page_size, total)} of {total} employees
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={filters.page === 1}
                      onClick={() => setFilters({ ...filters, page: filters.page - 1 })}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={filters.page * filters.page_size >= total}
                      onClick={() => setFilters({ ...filters, page: filters.page + 1 })}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

interface EmployeeFormProps {
  onSubmit: (data: EmployeeCreateInput) => void;
  departments: Array<{ id: string; name: string }>;
  initialData?: Employee;
}

function EmployeeForm({ onSubmit, departments, initialData }: EmployeeFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isEditing = !!initialData;

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);
    const formData = new FormData(e.currentTarget);
    const departmentId = formData.get('department_id') as string;
    const data: EmployeeCreateInput = {
      employee_id: formData.get('employee_id') as string || undefined,
      email: formData.get('email') as string,
      first_name: formData.get('first_name') as string,
      last_name: formData.get('last_name') as string,
      phone: formData.get('phone') as string || undefined,
      role: formData.get('role') as EmployeeRole,
      department_id: departmentId === '__none__' ? undefined : departmentId || undefined,
      status: formData.get('status') as EmployeeStatus,
      password: formData.get('password') as string,
      confirm_password: formData.get('confirm_password') as string,
    };
    await onSubmit(data);
    setIsSubmitting(false);
  };

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle>{isEditing ? 'Edit Employee' : 'Add New Employee'}</DialogTitle>
      </DialogHeader>
      <div className="grid gap-4 py-4">
        <div className="grid gap-2">
          <label htmlFor="employee_id" className="text-sm font-medium">Employee ID (Admin ID)</label>
          <Input
            id="employee_id"
            name="employee_id"
            placeholder="Auto-generated if empty"
            value={initialData?.employee_id || ''}
            disabled={isEditing}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
            <label htmlFor="first_name" className="text-sm font-medium">First Name *</label>
            <Input id="first_name" name="first_name" required defaultValue={initialData?.first_name || ''} />
          </div>
          <div className="grid gap-2">
            <label htmlFor="last_name" className="text-sm font-medium">Last Name *</label>
            <Input id="last_name" name="last_name" required defaultValue={initialData?.last_name || ''} />
          </div>
        </div>
        <div className="grid gap-2">
          <label htmlFor="email" className="text-sm font-medium">Email *</label>
          <Input id="email" name="email" type="email" required defaultValue={initialData?.email || ''} />
        </div>
        <div className="grid gap-2">
          <label htmlFor="phone" className="text-sm font-medium">Phone</label>
          <Input id="phone" name="phone" type="tel" defaultValue={initialData?.phone || ''} />
        </div>
        {!isEditing && (
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <label htmlFor="password" className="text-sm font-medium">Password *</label>
              <Input id="password" name="password" type="password" required minLength={12} placeholder="Min 12 characters" />
            </div>
            <div className="grid gap-2">
              <label htmlFor="confirm_password" className="text-sm font-medium">Confirm Password *</label>
              <Input id="confirm_password" name="confirm_password" type="password" required minLength={12} placeholder="Repeat password" />
            </div>
          </div>
        )}
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
            <label htmlFor="role" className="text-sm font-medium">Role *</label>
            <Select name="role" defaultValue={initialData?.role || 'employee'} required>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="employee">Employee</SelectItem>
                <SelectItem value="manager">Manager</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <label htmlFor="status" className="text-sm font-medium">Status *</label>
            <Select name="status" defaultValue={initialData?.status || 'active'} required>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="grid gap-2">
          <label htmlFor="department_id" className="text-sm font-medium">Department</label>
          <Select name="department_id" defaultValue="__none__">
            <SelectTrigger>
              <SelectValue placeholder="Select department" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">No department</SelectItem>
              {departments.map((dept) => (
                <SelectItem key={dept.id} value={dept.id}>{dept.name}</SelectItem>
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
          {isEditing ? 'Update Employee' : 'Create Employee'}
        </Button>
      </DialogFooter>
    </form>
  );
}
