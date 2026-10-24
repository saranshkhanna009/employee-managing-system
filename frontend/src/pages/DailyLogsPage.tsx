import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table';
import { Badge } from '../components/ui/Badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogClose } from '../components/ui/Dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '../components/ui/DropdownMenu';
import { apiClient } from '../utils/api';
import { DailyLog, DailyLogStatus, Task } from '../types';
import { formatDate } from '../utils/helpers';
import { Plus, Calendar, Clock, Trash2, Loader2, MoreVertical } from 'lucide-react';
import { toast } from 'sonner';

export function DailyLogsPage() {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();

  const [filters, setFilters] = useState({
    start_date: '',
    end_date: '',
    status: '',
    employee_id: searchParams.get('employee_id') || '',
    task_id: searchParams.get('task_id') || '',
    page: 1,
    page_size: 20,
  });

  const { data: logsData, isLoading } = useQuery({
    queryKey: ['daily-logs', filters],
    queryFn: () => apiClient.getDailyLogs(filters),
  });

  const { data: summary } = useQuery({
    queryKey: ['daily-summary', filters.start_date, filters.end_date],
    queryFn: () => apiClient.getMyDailySummary(filters.start_date, filters.end_date),
    enabled: !!filters.start_date && !!filters.end_date,
  });

  const createMutation = useMutation({
    mutationFn: (data: { task_id?: string; log_date: string; hours_spent?: number; progress_notes?: string; status?: string }) => apiClient.createDailyLog(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['daily-logs'] });
      queryClient.invalidateQueries({ queryKey: ['daily-summary'] });
      toast.success('Log entry created');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<DailyLog> }) => apiClient.updateDailyLog(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['daily-logs'] });
      queryClient.invalidateQueries({ queryKey: ['daily-summary'] });
      toast.success('Log entry updated');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteDailyLog(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['daily-logs'] });
      queryClient.invalidateQueries({ queryKey: ['daily-summary'] });
      toast.success('Log entry deleted');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const logs = logsData?.data.items || [];
  const total = logsData?.data.total || 0;

  const today = new Date().toISOString().split('T')[0];
  const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Daily Logs</h1>
          <p className="text-muted-foreground">Track your daily work progress</p>
        </div>
        <Dialog>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Add Log Entry
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DailyLogForm onSubmit={createMutation.mutate} />
          </DialogContent>
        </Dialog>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Hours</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.data.total_hours}h</div>
              <p className="text-xs text-muted-foreground">This period</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Tasks Logged</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.data.tasks_count}</div>
              <p className="text-xs text-muted-foreground">Unique tasks</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Completed</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.data.completed_tasks}</div>
              <p className="text-xs text-muted-foreground">Tasks completed</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">In Progress</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.data.in_progress_tasks}</div>
              <p className="text-xs text-muted-foreground">Tasks in progress</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Date Range Filter */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <Input
                type="date"
                value={filters.start_date || weekAgo}
                onChange={(e) => setFilters({ ...filters, start_date: e.target.value, page: 1 })}
                className="w-[200px]"
              />
              <span className="text-muted-foreground">to</span>
              <Input
                type="date"
                value={filters.end_date || today}
                onChange={(e) => setFilters({ ...filters, end_date: e.target.value, page: 1 })}
                className="w-[200px]"
              />
            </div>
            <Select value={filters.status} onValueChange={(value) => setFilters({ ...filters, status: value === '__all__' ? '' : value, page: 1 })}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All Statuses</SelectItem>
                <SelectItem value="not_started">Not Started</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="blocked">Blocked</SelectItem>
                <SelectItem value="on_hold">On Hold</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
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
                      <TableHead>Date</TableHead>
                      <TableHead>Task</TableHead>
                      <TableHead>Hours</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Notes</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.length > 0 ? (
                      logs.map((log: DailyLog) => (
                        <TableRow key={log.id}>
                          <TableCell>
                            <Calendar className="inline h-3 w-3 mr-1 text-muted-foreground" />
                            {formatDate(log.log_date)}
                          </TableCell>
                          <TableCell>
                            {log.task_title ? (
                              <Link to={`/tasks/${log.task_id}`} className="hover:underline">
                                {log.task_title}
                              </Link>
                            ) : (
                              <span className="text-muted-foreground">No task linked</span>
                            )}
                          </TableCell>
                          <TableCell>
                            {log.hours_spent ? `${log.hours_spent}h` : '-'}
                          </TableCell>
                          <TableCell>
                            <Badge variant="status" status={log.status}>
                              {log.status.replace('_', ' ')}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <p className="text-sm truncate max-w-xs">{log.progress_notes || '-'}</p>
                          </TableCell>
                          <TableCell className="text-right">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon">
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => updateMutation.mutate({ id: log.id, data: { status: 'completed' } })}>
                                  Mark Complete
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                  onClick={() => deleteMutation.mutate(log.id)}
                                  className="text-destructive focus:text-destructive"
                                >
                                  <Trash2 className="mr-2 h-4 w-4" />
                                  Delete
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                          No log entries for this period
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

function DailyLogForm({ onSubmit }: { onSubmit: (data: { task_id?: string; log_date: string; hours_spent?: number; progress_notes?: string; status?: string }) => void }) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    // Load user's tasks for the dropdown
    apiClient.getMyTasks().then(res => setTasks(res.data));
  }, []);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);
    const formData = new FormData(e.currentTarget);
    const taskId = formData.get('task_id') as string;
    const data = {
      task_id: taskId === '__none__' ? undefined : taskId || undefined,
      log_date: formData.get('log_date') as string,
      hours_spent: formData.get('hours_spent') ? parseFloat(formData.get('hours_spent') as string) : undefined,
      progress_notes: formData.get('progress_notes') as string,
      status: formData.get('status') as DailyLogStatus,
    };
    await onSubmit(data);
    setIsSubmitting(false);
  };

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle>Add Daily Log Entry</DialogTitle>
      </DialogHeader>
      <div className="grid gap-4 py-4">
        <div className="grid gap-2">
          <label htmlFor="log_date" className="text-sm font-medium">Date *</label>
          <Input id="log_date" name="log_date" type="date" required defaultValue={new Date().toISOString().split('T')[0]} />
        </div>
        <div className="grid gap-2">
          <label htmlFor="task_id" className="text-sm font-medium">Task (Optional)</label>
          <Select name="task_id" defaultValue="__none__">
            <SelectTrigger>
              <SelectValue placeholder="Select a task" />
            </SelectTrigger>
            <SelectContent>
                <SelectItem value="__none__">No task linked</SelectItem>
              {tasks.map((task: Task) => (
                <SelectItem key={task.id} value={task.id}>
                  {task.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
            <label htmlFor="hours_spent" className="text-sm font-medium">Hours Spent</label>
            <Input id="hours_spent" name="hours_spent" type="number" step="0.5" min="0" max="24" placeholder="e.g., 4" />
          </div>
          <div className="grid gap-2">
            <label htmlFor="status" className="text-sm font-medium">Status</label>
            <Select name="status" defaultValue="in_progress">
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="not_started">Not Started</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="blocked">Blocked</SelectItem>
                <SelectItem value="on_hold">On Hold</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="grid gap-2">
          <label htmlFor="progress_notes" className="text-sm font-medium">Progress Notes</label>
          <Textarea id="progress_notes" name="progress_notes" placeholder="What did you work on today?" rows={3} />
        </div>
      </div>
      <DialogFooter>
        <DialogClose asChild>
          <Button type="button" variant="outline">Cancel</Button>
        </DialogClose>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Save Entry
        </Button>
      </DialogFooter>
    </form>
  );
}
