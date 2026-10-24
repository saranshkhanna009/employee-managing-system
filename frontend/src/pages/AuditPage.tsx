import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select';
import { Card, CardContent } from '../components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table';
import { Badge } from '../components/ui/Badge';
import { apiClient } from '../utils/api';
import { useAuthStore } from '../store/auth';
import { formatDate } from '../utils/helpers';
import { Search, Download, Eye, ChevronLeft, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';

interface AuditLog {
  id: string;
  company_id: string;
  employee_id: string | null;
  employee_name: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  user_agent: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export function AuditPage() {
  const { hasRole } = useAuthStore();
  const isAdminOrAbove = hasRole('admin', 'super_admin');

  const [filters, setFilters] = useState({
    action: '',
    resource_type: '',
    employee_id: '',
    start_date: '',
    end_date: '',
    page: 1,
    page_size: 50,
  });

  const { data: auditData, isLoading } = useQuery({
    queryKey: ['audit', filters],
    queryFn: () => apiClient.getAuditLogs(filters),
    enabled: isAdminOrAbove,
  });

  const { data: employees } = useQuery({
    queryKey: ['employees', 'all'],
    queryFn: () => apiClient.getEmployees({ page_size: 200 }),
    select: (res) => res.data.items,
    enabled: isAdminOrAbove,
  });

  const exportMutation = useMutation({
    mutationFn: (exportFilters: typeof filters) => apiClient.exportAuditLogs(exportFilters),
    onSuccess: (data) => {
      const blob = data.data instanceof Blob
        ? data.data
        : new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Audit logs exported');
    },
    onError: (err: Error) => toast.error(err.message),
    // This mutation is only reachable from the authorized page.
  });

  if (!isAdminOrAbove) {
    return (
      <div className="space-y-6">
        <Card>
          <CardContent className="py-12 text-center">
            <h2 className="text-xl font-semibold mb-2">Access Denied</h2>
            <p className="text-muted-foreground mb-4">You need administrator privileges to view audit logs.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const logs = auditData?.data.items || [];
  const total = auditData?.data.total || 0;

  const actionColors: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
    LOGIN: 'default',
    LOGOUT: 'secondary',
    LOGIN_FAILED: 'destructive',
    PASSWORD_CHANGED: 'default',
    COMPANY_CREATED: 'default',
    COMPANY_UPDATED: 'secondary',
    COMPANY_DELETED: 'destructive',
    DEPARTMENT_CREATED: 'default',
    DEPARTMENT_UPDATED: 'secondary',
    DEPARTMENT_DELETED: 'destructive',
    EMPLOYEE_CREATED: 'default',
    EMPLOYEE_UPDATED: 'secondary',
    EMPLOYEE_DELETED: 'destructive',
    EMPLOYEE_PASSWORD_RESET: 'default',
    TASK_CREATED: 'default',
    TASK_UPDATED: 'secondary',
    TASK_DELETED: 'destructive',
    TASK_ASSIGNED: 'default',
    TASK_STATUS_CHANGED: 'default',
    DAILY_LOG_CREATED: 'default',
    DAILY_LOG_UPDATED: 'secondary',
    DAILY_LOG_DELETED: 'destructive',
    LEAVE_CREATED: 'default',
    LEAVE_UPDATED: 'secondary',
    LEAVE_REVIEWED: 'default',
    SESSION_REVOKED: 'secondary',
    DATA_EXPORTED: 'default',
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Audit Logs</h1>
          <p className="text-muted-foreground">View system audit trail for security and compliance</p>
        </div>
        <Button onClick={() => exportMutation.mutate(filters)} disabled={exportMutation.isPending}>
          <Download className="mr-2 h-4 w-4" />
          {exportMutation.isPending ? 'Exporting...' : 'Export'}
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search actions..."
                value={filters.action}
                onChange={(e) => setFilters({ ...filters, action: e.target.value, page: 1 })}
                className="pl-10"
              />
            </div>
            <Select value={filters.resource_type} onValueChange={(value) => setFilters({ ...filters, resource_type: value === '__all__' ? '' : value, page: 1 })}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Resources" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All Resources</SelectItem>
                <SelectItem value="company">Company</SelectItem>
                <SelectItem value="department">Department</SelectItem>
                <SelectItem value="employee">Employee</SelectItem>
                <SelectItem value="task">Task</SelectItem>
                <SelectItem value="daily_log">Daily Log</SelectItem>
                <SelectItem value="leave">Leave</SelectItem>
                <SelectItem value="session">Session</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filters.employee_id} onValueChange={(value) => setFilters({ ...filters, employee_id: value === '__all__' ? '' : value, page: 1 })}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="All Employees" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All Employees</SelectItem>
                {employees?.map((emp: { id: string; first_name: string; last_name: string; employee_id: string }) => (
                  <SelectItem key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name} ({emp.employee_id})</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="flex items-center gap-2">
              <Input
                type="date"
                value={filters.start_date}
                onChange={(e) => setFilters({ ...filters, start_date: e.target.value, page: 1 })}
                className="w-[160px]"
                placeholder="From"
              />
              <span className="text-muted-foreground">to</span>
              <Input
                type="date"
                value={filters.end_date}
                onChange={(e) => setFilters({ ...filters, end_date: e.target.value, page: 1 })}
                className="w-[160px]"
                placeholder="To"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Audit Table */}
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
                      <TableHead className="w-[160px]">Timestamp</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead className="w-[120px]">Resource</TableHead>
                      <TableHead className="w-[180px]">Employee</TableHead>
                      <TableHead className="w-[140px]">IP Address</TableHead>
                      <TableHead>Details</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.length > 0 ? (
                      logs.map((log: AuditLog) => (
                        <TableRow key={log.id}>
                          <TableCell className="font-mono text-sm">{formatDate(log.created_at)}</TableCell>
                          <TableCell>
                            <Badge variant={actionColors[log.action] || 'default'}>
                              {log.action.replace(/_/g, ' ')}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {log.resource_type ? (
                              <span className="font-mono text-sm">{log.resource_type}:{log.resource_id?.slice(0, 8)}</span>
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </TableCell>
                          <TableCell>
                            {log.employee_name ? (
                              <span>{log.employee_name}</span>
                            ) : log.employee_id ? (
                              <span className="font-mono text-sm text-muted-foreground">{log.employee_id.slice(0, 8)}...</span>
                            ) : (
                              <span className="text-muted-foreground">System</span>
                            )}
                          </TableCell>
                          <TableCell>
                            {log.ip_address ? (
                              <span className="font-mono text-sm">{log.ip_address}</span>
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                alert(JSON.stringify(log.metadata, null, 2));
                              }}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                          No audit logs found
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
                    {Math.min(filters.page * filters.page_size, total)} of {total} entries
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={filters.page === 1 || exportMutation.isPending}
                      onClick={() => setFilters({ ...filters, page: filters.page - 1 })}
                    >
                      <ChevronLeft className="mr-1 h-4 w-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={filters.page * filters.page_size >= total || exportMutation.isPending}
                      onClick={() => setFilters({ ...filters, page: filters.page + 1 })}
                    >
                      Next <ChevronRight className="ml-1 h-4 w-4" />
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
