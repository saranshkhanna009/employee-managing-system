import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table';
import { Badge } from '../components/ui/Badge';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '../components/ui/DropdownMenu';
import { apiClient } from '../utils/api';
import { Employee } from '../types';
import { useAuthStore } from '../store/auth';
import { formatDate } from '../utils/helpers';
import { Search, MoreVertical, Edit, Users, Calendar, ClipboardList, TrendingUp, User } from 'lucide-react';

export function TeamPage() {
  const { user, hasRole } = useAuthStore();
  const isManagerOrAbove = hasRole('manager', 'admin', 'super_admin');
  const navigate = useNavigate();

  const [filters, setFilters] = useState({
    search: '',
    status: '',
    page: 1,
    page_size: 20,
  });

  const { data: teamData, isLoading } = useQuery({
    queryKey: ['team', filters],
    queryFn: () => apiClient.getTeamMembers(filters),
    enabled: isManagerOrAbove,
  });

  const { data: teamSummary } = useQuery({
    queryKey: ['team-summary'],
    queryFn: () => apiClient.getTeamSummary(),
    enabled: isManagerOrAbove,
  });

  const employees = teamData?.data.items || [];
  const total = teamData?.data.total || 0;

  if (!isManagerOrAbove) {
    return (
      <div className="space-y-6">
        <Card>
          <CardContent className="py-12 text-center">
            <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">Access Denied</h2>
            <p className="text-muted-foreground">You need manager privileges to view the team page.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Team Management</h1>
          <p className="text-muted-foreground">View and manage your team members</p>
        </div>
      </div>

      {/* Team Summary */}
      {teamSummary && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Team Members</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
               <div className="text-2xl font-bold">{teamSummary.data.total_members}</div>
              <p className="text-xs text-muted-foreground">Active employees</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Tasks Assigned</CardTitle>
              <ClipboardList className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
               <div className="text-2xl font-bold">{teamSummary.data.total_tasks}</div>
              <p className="text-xs text-muted-foreground">Total team tasks</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Completed This Week</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
               <div className="text-2xl font-bold">{teamSummary.data.completed_this_week}</div>
              <p className="text-xs text-muted-foreground">Tasks completed</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Hours Logged Today</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
               <div className="text-2xl font-bold">{teamSummary.data.hours_today}h</div>
              <p className="text-xs text-muted-foreground">Total team hours</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search team members..."
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value, page: 1 })}
                className="pl-10"
              />
            </div>
            <Select value={filters.status} onValueChange={(value) => setFilters({ ...filters, status: value === '__all__' ? '' : value, page: 1 })}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All Statuses</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Team Members Table */}
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
              {employees.length > 0 ? (
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Team Member</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead>Department</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Tasks</TableHead>
                        <TableHead>Last Active</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {employees.map((emp: Employee) => (
                        <TableRow key={emp.id}>
                          <TableCell>
                            <Link to={`/employees/${emp.id}`} className="font-medium hover:underline flex items-center gap-2">
                              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                                <User className="h-4 w-4 text-primary" />
                              </div>
                              <div>
                                <p>{emp.first_name} {emp.last_name}</p>
                                <p className="text-sm text-muted-foreground">{emp.employee_id}</p>
                              </div>
                            </Link>
                          </TableCell>
                          <TableCell>
                            <Badge variant={emp.role === 'admin' ? 'secondary' : emp.role === 'manager' ? 'default' : 'outline'}>
                              {emp.role === 'admin' ? 'Admin' : emp.role === 'manager' ? 'Manager' : 'Employee'}
                            </Badge>
                          </TableCell>
                          <TableCell>{emp.department_name || 'Not assigned'}</TableCell>
                          <TableCell>
                            <Badge variant={emp.status === 'active' ? 'default' : emp.status === 'locked' ? 'destructive' : 'secondary'}>
                              {emp.status}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <ClipboardList className="h-4 w-4 text-muted-foreground" />
                               <span>{emp.task_count || 0}</span>
                            </div>
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
                                  <Link to={`/employees/${emp.id}`}>View Profile</Link>
                                </DropdownMenuItem>
                                <DropdownMenuItem asChild>
                                  <Link to={`/tasks?assigned_to=${emp.id}`}>View Tasks</Link>
                                </DropdownMenuItem>
                                <DropdownMenuItem asChild>
                                  <Link to={`/leaves?employee_id=${emp.id}`}>View Leave Requests</Link>
                                </DropdownMenuItem>
                                <DropdownMenuItem asChild>
                                  <Link to={`/daily-logs?employee_id=${emp.id}`}>View Daily Logs</Link>
                                </DropdownMenuItem>
                                {hasRole('admin', 'super_admin') && emp.id !== user?.id && (
                                  <>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem onClick={() => navigate(`/employees/${emp.id}`)}>
                                      <Edit className="mr-2 h-4 w-4" />
                                      Edit Employee
                                    </DropdownMenuItem>
                                  </>
                                )}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="text-center py-12">
                  <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-medium mb-2">No team members found</h3>
                  <p className="text-muted-foreground">Your team will appear here once employees are assigned to your department.</p>
                </div>
              )}

              {/* Pagination */}
              {total > filters.page_size && (
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-muted-foreground">
                    Showing {(filters.page - 1) * filters.page_size + 1} to{' '}
                    {Math.min(filters.page * filters.page_size, total)} of {total} members
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
