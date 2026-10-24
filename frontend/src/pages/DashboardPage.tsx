import { useAuthStore } from '../store/auth';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { formatRelativeTime, cn } from '../utils/helpers';
import {
  ClipboardList,
  Calendar,
  FileText,
  Users,
  ArrowRight,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiClient } from '../utils/api';
import { useQuery } from '@tanstack/react-query';
import { DepartmentDailySummary, LeaveRequest, Task, TaskSummary } from '../types';

export function DashboardPage() {
  const { user, hasRole } = useAuthStore();
  const isManagerOrAbove = hasRole('manager', 'admin', 'super_admin');

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const [tasksRes, leavesRes, teamRes] = await Promise.all([
        apiClient.getMyTasks(),
        apiClient.getLeaveBalance(),
        isManagerOrAbove && user?.department_id
          ? apiClient.get<DepartmentDailySummary>(`/daily-logs/department/${user?.department_id}/summary`, {
              params: { log_date: new Date().toISOString().split('T')[0] },
            })
          : Promise.resolve({ data: null }),
      ]);
      const taskItems: TaskSummary[] = tasksRes.data;
      const leaveBalance = leavesRes.data;
      const leaveRequests: LeaveRequest[] = (await apiClient.getLeaves({ page_size: 100 })).data.items;
      return {
        myTasks: {
          total: taskItems.length,
          pending: taskItems.filter((task) => task.status === 'pending').length,
          inProgress: taskItems.filter((task) => task.status === 'in_progress').length,
          completed: taskItems.filter((task) => task.status === 'completed').length,
          overdue: 0,
        },
        myLeaves: {
          total: leaveRequests.length,
          pending: leaveRequests.filter((leave) => leave.status === 'pending').length,
          approved: leaveRequests.filter((leave) => leave.status === 'approved').length,
          used: leaveBalance.balances.reduce((sum, balance) => sum + balance.used, 0),
          remaining: leaveBalance.balances.reduce((sum, balance) => sum + balance.remaining, 0),
        },
        teamStats: teamRes.data
          ? {
              activeToday: teamRes.data.active_employees,
              tasksCompletedToday: teamRes.data.tasks_completed,
              hoursLoggedToday: teamRes.data.total_hours,
            }
          : null,
      };
    },
  });

  const { data: recentTasks } = useQuery({
    queryKey: ['recent-tasks'],
    queryFn: () => apiClient.getMyTasks(),
    select: (res) => res.data.slice(0, 5),
  });

  const { data: recentLeaves } = useQuery({
    queryKey: ['recent-leaves'],
    queryFn: () => apiClient.getLeaves({ page_size: 5 }),
    select: (res) => res.data.items.slice(0, 5),
  });

  if (!user) return null;

  const taskStats = stats?.myTasks || { total: 0, pending: 0, inProgress: 0, completed: 0, overdue: 0 };
  const leaveStats = stats?.myLeaves || { total: 0, pending: 0, approved: 0, used: 0, remaining: 0 };

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Welcome back, {user.first_name}</h1>
          <p className="text-muted-foreground">
            Here's what's happening with your tasks and leave requests today.
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild>
            <Link to="/tasks">View Tasks</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/leaves">View Leave Requests</Link>
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">My Tasks</CardTitle>
            <ClipboardList className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{taskStats.total}</div>
            <p className="text-xs text-muted-foreground">Total assigned tasks</p>
            <div className="flex gap-2 mt-2 text-xs">
              <Badge variant="status" status="pending">{taskStats.pending} Pending</Badge>
              <Badge variant="status" status="in_progress">{taskStats.inProgress} In Progress</Badge>
              <Badge variant="status" status="completed">{taskStats.completed} Done</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Leave Balance</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{leaveStats.remaining}</div>
            <p className="text-xs text-muted-foreground">Days remaining this year</p>
            <div className="flex gap-2 mt-2 text-xs">
              <Badge variant="status" status="approved">{leaveStats.approved} Approved</Badge>
              <Badge variant="status" status="pending">{leaveStats.pending} Pending</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Leave Requests</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{leaveStats.total}</div>
            <p className="text-xs text-muted-foreground">Total requests this year</p>
            <div className="flex gap-2 mt-2 text-xs">
              <Badge variant="status" status="approved">{leaveStats.approved} Approved</Badge>
              <Badge variant="status" status="pending">{leaveStats.pending} Pending</Badge>
            </div>
          </CardContent>
        </Card>

        {isManagerOrAbove && stats?.teamStats && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Team Today</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.teamStats.activeToday}</div>
              <p className="text-xs text-muted-foreground">Active team members</p>
              <div className="flex gap-2 mt-2 text-xs">
                <Badge variant="default">{stats.teamStats.tasksCompletedToday} Tasks Done</Badge>
                <Badge variant="secondary">{stats.teamStats.hoursLoggedToday}h Logged</Badge>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Recent Activity */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Recent Tasks */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Tasks</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/tasks">View all <ArrowRight className="ml-1 h-4 w-4" /></Link>
            </Button>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 animate-pulse bg-muted rounded" />
                ))}
              </div>
            ) : recentTasks && recentTasks.length > 0 ? (
              <div className="space-y-3">
                {recentTasks.map((task: Task) => (
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
                        {task.is_overdue ? 'Overdue' : 'Due'} {formatRelativeTime(task.due_date)}
                      </p>
                    )}
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <ClipboardList className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No tasks assigned yet</p>
                <Button variant="link" asChild className="mt-2">
                  <Link to="/tasks">View all tasks</Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Leave Requests */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Leave Requests</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/leaves">View all <ArrowRight className="ml-1 h-4 w-4" /></Link>
            </Button>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 animate-pulse bg-muted rounded" />
                ))}
              </div>
            ) : recentLeaves && recentLeaves.length > 0 ? (
              <div className="space-y-3">
                {recentLeaves.map((leave: LeaveRequest) => (
                  <Link key={leave.id} to={`/leaves/${leave.id}`} className="block hover:bg-accent rounded-lg p-3 transition-colors">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="font-medium capitalize truncate">{leave.leave_type.replace('_', ' ')}</p>
                        <p className="text-sm text-muted-foreground">
                          {new Date(leave.start_date).toLocaleDateString()} - {new Date(leave.end_date).toLocaleDateString()}
                        </p>
                      </div>
                      <Badge variant="status" status={leave.status}>{leave.status}</Badge>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No leave requests yet</p>
                <Button variant="link" asChild className="mt-2">
                  <Link to="/leaves">Open leave requests</Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
