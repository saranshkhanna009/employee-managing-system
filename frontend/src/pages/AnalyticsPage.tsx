import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table';
import { apiClient } from '../utils/api';
import { useAuthStore } from '../store/auth';
import { formatDate } from '../utils/helpers';
import { Users, ClipboardList, FileText, Calendar, TrendingUp, Building2 } from 'lucide-react';

interface AnalyticsData {
  overview: {
    total_employees: number;
    total_tasks: number;
    completed_tasks: number;
    total_hours: number;
    leave_requests: number;
    approved_leaves: number;
  };
  tasks_by_status: Array<{ status: string; count: number }>;
  tasks_by_priority: Array<{ priority: string; count: number }>;
  leaves_by_type: Array<{ leave_type: string; count: number }>;
  leaves_by_status: Array<{ status: string; count: number }>;
  daily_activity: Array<{ date: string; hours: number; tasks: number }>;
  department_stats: Array<{ department: string; employees: number; tasks: number; hours: number }>;
  top_performers: Array<{ employee_id: string; name: string; tasks_completed: number; hours: number }>;
}

export function AnalyticsPage() {
  const { hasRole } = useAuthStore();
  const isAdminOrAbove = hasRole('admin', 'super_admin');

  const [dateRange, setDateRange] = useState('30d');

  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analytics', dateRange],
    queryFn: () => apiClient.getAnalytics(dateRange),
    enabled: isAdminOrAbove,
  });

  const data = analytics?.data as AnalyticsData | undefined;

  if (!isAdminOrAbove) {
    return (
      <div className="space-y-6">
        <Card>
          <CardContent className="py-12 text-center">
            <Building2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">Access Denied</h2>
            <p className="text-muted-foreground">You need administrator privileges to view analytics.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
            <p className="text-muted-foreground">Company-wide insights and reports</p>
          </div>
          <Select value={dateRange} onValueChange={setDateRange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 Days</SelectItem>
              <SelectItem value="30d">Last 30 Days</SelectItem>
              <SelectItem value="90d">Last 90 Days</SelectItem>
              <SelectItem value="1y">Last Year</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardContent className="py-6">
                <div className="h-8 animate-pulse bg-muted rounded w-3/4" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {[1, 2].map((i) => (
            <Card key={i}>
              <CardContent className="py-6">
                <div className="h-64 animate-pulse bg-muted rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
            <p className="text-muted-foreground">Company-wide insights and reports</p>
          </div>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <TrendingUp className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">No Data Available</h2>
            <p className="text-muted-foreground">Analytics data will appear once there is activity in the system.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { overview, tasks_by_status, tasks_by_priority, leaves_by_type, leaves_by_status, daily_activity, department_stats, top_performers } = data;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
          <p className="text-muted-foreground">Company-wide insights and reports</p>
        </div>
        <Select value={dateRange} onValueChange={setDateRange}>
          <SelectTrigger className="w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7d">Last 7 Days</SelectItem>
            <SelectItem value="30d">Last 30 Days</SelectItem>
            <SelectItem value="90d">Last 90 Days</SelectItem>
            <SelectItem value="1y">Last Year</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Employees</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview.total_employees}</div>
            <p className="text-xs text-muted-foreground">Active employees</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Tasks</CardTitle>
            <ClipboardList className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview.total_tasks}</div>
            <p className="text-xs text-muted-foreground">All tasks</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview.completed_tasks}</div>
            <p className="text-xs text-muted-foreground">
              {overview.total_tasks > 0
                ? `${Math.round((overview.completed_tasks / overview.total_tasks) * 100)}% completion rate`
                : '0% completion rate'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Hours</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview.total_hours}h</div>
            <p className="text-xs text-muted-foreground">Logged this period</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Leave Requests</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview.leave_requests}</div>
            <p className="text-xs text-muted-foreground">
              {overview.approved_leaves} approved
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Hours/Employee</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {overview.total_employees > 0
                ? (overview.total_hours / overview.total_employees).toFixed(1)
                : '0'}
            </div>
            <p className="text-xs text-muted-foreground">Per employee</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Section */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Tasks by Status */}
        <Card>
          <CardHeader>
            <CardTitle>Tasks by Status</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <div className="h-full flex items-end justify-center gap-4 p-4">
              {tasks_by_status.map((item) => (
                <div key={item.status} className="flex flex-col items-center flex-1">
                  <div
                    className="w-full bg-primary transition-all hover:opacity-80 rounded-t"
                    style={{
                      height: `${Math.max((item.count / Math.max(...tasks_by_status.map(t => t.count), 1)) * 100, 5)}%`,
                      minHeight: '20px',
                    }}
                    title={`${item.status}: ${item.count}`}
                  />
                  <span className="text-xs text-muted-foreground mt-2 text-center capitalize">{item.status.replace('_', ' ')}</span>
                  <span className="text-sm font-medium">{item.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Tasks by Priority */}
        <Card>
          <CardHeader>
            <CardTitle>Tasks by Priority</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <div className="h-full flex items-end justify-center gap-4 p-4">
              {tasks_by_priority.map((item) => (
                <div key={item.priority} className="flex flex-col items-center flex-1">
                  <div
                    className={`w-full transition-all hover:opacity-80 rounded-t ${
                      item.priority === 'urgent' ? 'bg-destructive' :
                      item.priority === 'high' ? 'bg-orange-500' :
                      item.priority === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                    }`}
                    style={{
                      height: `${Math.max((item.count / Math.max(...tasks_by_priority.map(t => t.count), 1)) * 100, 5)}%`,
                      minHeight: '20px',
                    }}
                    title={`${item.priority}: ${item.count}`}
                  />
                  <span className="text-xs text-muted-foreground mt-2 text-center capitalize">{item.priority}</span>
                  <span className="text-sm font-medium">{item.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Leaves by Type */}
        <Card>
          <CardHeader>
            <CardTitle>Leave Requests by Type</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <div className="h-full flex items-end justify-center gap-4 p-4">
              {leaves_by_type.map((item) => (
                <div key={item.leave_type} className="flex flex-col items-center flex-1">
                  <div
                    className="w-full bg-blue-500 transition-all hover:opacity-80 rounded-t"
                    style={{
                      height: `${Math.max((item.count / Math.max(...leaves_by_type.map(t => t.count), 1)) * 100, 5)}%`,
                      minHeight: '20px',
                    }}
                    title={`${item.leave_type}: ${item.count}`}
                  />
                  <span className="text-xs text-muted-foreground mt-2 text-center capitalize">{item.leave_type.replace('_', ' ')}</span>
                  <span className="text-sm font-medium">{item.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Leaves by Status */}
        <Card>
          <CardHeader>
            <CardTitle>Leave Requests by Status</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <div className="h-full flex items-end justify-center gap-4 p-4">
              {leaves_by_status.map((item) => (
                <div key={item.status} className="flex flex-col items-center flex-1">
                  <div
                    className={`w-full transition-all hover:opacity-80 rounded-t ${
                      item.status === 'approved' ? 'bg-green-500' :
                      item.status === 'pending' ? 'bg-yellow-500' :
                      item.status === 'rejected' ? 'bg-red-500' : 'bg-gray-500'
                    }`}
                    style={{
                      height: `${Math.max((item.count / Math.max(...leaves_by_status.map(t => t.count), 1)) * 100, 5)}%`,
                      minHeight: '20px',
                    }}
                    title={`${item.status}: ${item.count}`}
                  />
                  <span className="text-xs text-muted-foreground mt-2 text-center capitalize">{item.status}</span>
                  <span className="text-sm font-medium">{item.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Daily Activity Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Daily Activity (Hours Logged)</CardTitle>
        </CardHeader>
        <CardContent className="h-64">
          <div className="h-full flex items-end justify-center gap-1 p-4 overflow-x-auto">
            {daily_activity.map((item) => (
              <div key={item.date} className="flex flex-col items-center flex-shrink-0" style={{ minWidth: '40px' }}>
                <div
                  className="w-full bg-primary transition-all hover:opacity-80 rounded-t"
                  style={{
                    height: `${Math.max((item.hours / Math.max(...daily_activity.map(t => t.hours), 1)) * 100, 5)}%`,
                    minHeight: '20px',
                  }}
                  title={`${formatDate(item.date)}: ${item.hours}h (${item.tasks} tasks)`}
                />
                <span className="text-xs text-muted-foreground mt-1">{formatDate(item.date).split(' ')[0]}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Department Stats & Top Performers */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Department Stats */}
        <Card>
          <CardHeader>
            <CardTitle>Department Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Department</TableHead>
                    <TableHead className="text-right">Employees</TableHead>
                    <TableHead className="text-right">Tasks</TableHead>
                    <TableHead className="text-right">Hours</TableHead>
                    <TableHead className="text-right">Avg Hours/Emp</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {department_stats.map((dept) => (
                    <TableRow key={dept.department}>
                      <TableCell className="font-medium">{dept.department}</TableCell>
                      <TableCell className="text-right">{dept.employees}</TableCell>
                      <TableCell className="text-right">{dept.tasks}</TableCell>
                      <TableCell className="text-right">{dept.hours}h</TableCell>
                      <TableCell className="text-right">
                        {dept.employees > 0 ? (dept.hours / dept.employees).toFixed(1) : '0'}h
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        {/* Top Performers */}
        <Card>
          <CardHeader>
            <CardTitle>Top Performers</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {top_performers.length > 0 ? (
                top_performers.map((performer, index) => (
                  <div key={performer.employee_id} className="flex items-center gap-4 p-3 bg-muted/50 rounded-lg">
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
                      {index + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{performer.name}</p>
                      <p className="text-sm text-muted-foreground">{performer.employee_id}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-medium">{performer.tasks_completed} tasks</p>
                      <p className="text-sm text-muted-foreground">{performer.hours}h logged</p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-center py-8 text-muted-foreground">No performance data available</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
