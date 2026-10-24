import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../components/ui/DropdownMenu';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '../components/ui/Dialog';
import { apiClient } from '../utils/api';
import { TaskStatus, DailyLog } from '../types';
import { useAuthStore } from '../store/auth';
import { formatDate, cn } from '../utils/helpers';
import { ArrowLeft, Trash2, Calendar, Flag, User, Loader2, Clock, Plus, MoreVertical } from 'lucide-react';
import { toast } from 'sonner';

export function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, hasRole } = useAuthStore();
  const isManagerOrAbove = hasRole('manager', 'admin', 'super_admin');
  const canEdit = isManagerOrAbove;

  const { data: task, isLoading } = useQuery({
    queryKey: ['task', id],
    queryFn: () => apiClient.getTask(id!),
    enabled: !!id,
  });

  const { data: logsData } = useQuery({
    queryKey: ['task-logs', id],
    queryFn: () => apiClient.getDailyLogs({ task_id: id, page_size: 20 }),
    enabled: !!id,
  });

  const updateStatusMutation = useMutation({
    mutationFn: (status: TaskStatus) => apiClient.updateTaskStatus(id!, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', id] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success('Status updated');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: () => apiClient.deleteTask(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success('Task deleted');
      navigate('/tasks');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const assignMutation = useMutation({
    mutationFn: (assignedToId: string) => apiClient.assignTask(id!, assignedToId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', id] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success('Task assigned');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const createLogMutation = useMutation({
    mutationFn: (data: { log_date: string; hours_spent?: number; progress_notes?: string; status?: string }) =>
      apiClient.createDailyLog({ ...data, task_id: id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task-logs', id] });
      toast.success('Log entry added');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  if (!id) return null;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" onClick={() => navigate('/tasks')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <h1 className="text-3xl font-bold tracking-tight">Task Details</h1>
        </div>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse bg-muted rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (!task?.data) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" onClick={() => navigate('/tasks')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <h1 className="text-3xl font-bold tracking-tight">Task Details</h1>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <h2 className="text-xl font-semibold mb-2">Task Not Found</h2>
            <p className="text-muted-foreground mb-4">This task may have been deleted or you don't have permission to view it.</p>
            <Button onClick={() => navigate('/tasks')}>Back to Tasks</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const taskData = task.data;
  const logs = logsData?.data.items || [];
  const isAssignee = taskData.assigned_to_id === user?.id;
  const canUpdateStatus = isAssignee || isManagerOrAbove;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" onClick={() => navigate('/tasks')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{taskData.title}</h1>
            <p className="text-muted-foreground">{taskData.department_name || 'No department'}</p>
          </div>
        </div>
        {canEdit && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                <MoreVertical className="mr-2 h-4 w-4" />
                Actions
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={() => {
                  if (confirm('Are you sure you want to delete this task?')) {
                    deleteMutation.mutate();
                  }
                }}
                className="text-destructive focus:text-destructive"
                disabled={deleteMutation.isPending}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                {deleteMutation.isPending ? 'Deleting...' : 'Delete Task'}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          {/* Status & Priority */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Status & Progress</CardTitle>
                <div className="flex items-center gap-2">
                  <Badge variant="status" status={taskData.status}>
                    {taskData.status.replace('_', ' ')}
                  </Badge>
                  <Badge variant="priority" priority={taskData.priority}>
                    {taskData.priority}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {canUpdateStatus && (
                <div className="flex flex-wrap gap-2">
                  {(['pending', 'in_progress', 'in_review', 'completed', 'blocked', 'cancelled'] as TaskStatus[]).map((status) => (
                    <Button
                      key={status}
                      variant={taskData.status === status ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => updateStatusMutation.mutate(status)}
                      disabled={updateStatusMutation.isPending || taskData.status === status}
                    >
                      {status.replace('_', ' ')}
                    </Button>
                  ))}
                </div>
              )}

              <div className="grid gap-4 md:grid-cols-2 pt-4 border-t">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Assignee</label>
                  <p className="flex items-center gap-2">
                    <User className="h-4 w-4 text-muted-foreground" />
                    {taskData.assigned_to_name || <span className="text-muted-foreground">Unassigned</span>}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Created By</label>
                  <p className="flex items-center gap-2">
                    <User className="h-4 w-4 text-muted-foreground" />
                     {taskData.created_by_name || 'Unknown'}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Due Date</label>
                  <p className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    {taskData.due_date ? (
                      <span className={cn(taskData.is_overdue && 'text-destructive')}>
                        {formatDate(taskData.due_date)}
                        {taskData.is_overdue && ' (Overdue)'}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">No due date</span>
                    )}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Estimated Hours</label>
                  <p className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    {taskData.estimated_hours ? `${taskData.estimated_hours}h` : 'Not set'}
                  </p>
                </div>
              </div>

              {taskData.description && (
                <div className="pt-4 border-t">
                  <label className="text-sm font-medium text-muted-foreground">Description</label>
                  <p className="mt-1 whitespace-pre-wrap">{taskData.description}</p>
                </div>
              )}

              {taskData.completed_at && (
                <div className="pt-4 border-t text-sm text-muted-foreground">
                  Completed: {formatDate(taskData.completed_at)}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Daily Logs Tab */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Daily Logs</CardTitle>
                <Dialog>
                  <DialogTrigger asChild>
                    <Button size="sm">
                      <Plus className="mr-2 h-4 w-4" />
                      Add Log
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <AddLogForm onSubmit={createLogMutation.mutate} />
                  </DialogContent>
                </Dialog>
              </div>
            </CardHeader>
            <CardContent>
              {logs.length > 0 ? (
                <div className="space-y-3">
                  {logs.map((log: DailyLog) => (
                    <div key={log.id} className="p-3 border rounded-lg hover:bg-accent transition-colors">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-3">
                          <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center">
                            <Clock className="h-4 w-4 text-muted-foreground" />
                          </div>
                          <div>
                            <p className="font-medium">{formatDate(log.log_date)}</p>
                            <p className="text-sm text-muted-foreground">
                              {log.hours_spent ? `${log.hours_spent}h` : 'No hours'} • {log.status.replace('_', ' ')}
                            </p>
                          </div>
                        </div>
                        <Badge variant="status" status={log.status}>
                          {log.status.replace('_', ' ')}
                        </Badge>
                      </div>
                      {log.progress_notes && (
                        <p className="mt-2 text-sm text-muted-foreground">{log.progress_notes}</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center py-8 text-muted-foreground">No daily logs for this task yet</p>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          {/* Task Info */}
          <Card>
            <CardHeader>
              <CardTitle>Task Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3">
                <div className="p-3 bg-muted/50 rounded-lg">
                  <p className="text-xs text-muted-foreground">Task ID</p>
                  <p className="font-mono text-sm">{taskData.id}</p>
                </div>
                <div className="p-3 bg-muted/50 rounded-lg">
                  <p className="text-xs text-muted-foreground">Created</p>
                  <p>{formatDate(taskData.created_at)}</p>
                </div>
                <div className="p-3 bg-muted/50 rounded-lg">
                  <p className="text-xs text-muted-foreground">Updated</p>
                  <p>{formatDate(taskData.updated_at)}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Assign Task */}
          {canEdit && (
            <Card>
              <CardHeader>
                <CardTitle>Assign Task</CardTitle>
              </CardHeader>
              <CardContent>
                <AssignTaskForm
                  currentAssigneeId={taskData.assigned_to_id}
                  onAssign={assignMutation.mutate}
                  isPending={assignMutation.isPending}
                />
              </CardContent>
            </Card>
          )}

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" className="w-full justify-start" onClick={() => navigate(`/daily-logs?task_id=${taskData.id}`)}>
                <Plus className="mr-2 h-4 w-4" />
                Log Time
              </Button>
              <Button variant="outline" className="w-full justify-start" onClick={() => navigate(`/tasks?department_id=${taskData.department_id}`)}>
                <Flag className="mr-2 h-4 w-4" />
                View Department Tasks
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function AddLogForm({ onSubmit }: { onSubmit: (data: { log_date: string; hours_spent?: number; progress_notes?: string; status?: string }) => void }) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);
    const formData = new FormData(e.currentTarget);
    const data = {
      log_date: formData.get('log_date') as string,
      hours_spent: formData.get('hours_spent') ? parseFloat(formData.get('hours_spent') as string) : undefined,
      progress_notes: formData.get('progress_notes') as string,
      status: (formData.get('status') as string) || 'in_progress',
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
        <Button type="button" variant="outline" onClick={() => { }}>Cancel</Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Save Entry
        </Button>
      </DialogFooter>
    </form>
  );
}

function AssignTaskForm({ currentAssigneeId, onAssign, isPending }: { currentAssigneeId?: string | null; onAssign: (assignedToId: string) => void; isPending: boolean }) {
  const [selectedUser, setSelectedUser] = useState<string>('');
  const [search, setSearch] = useState('');

  const { data: employees } = useQuery({
    queryKey: ['employees-for-assign', search],
    queryFn: () => apiClient.getEmployees({ search, page_size: 50, status: 'active' }),
    select: (res) => res.data.items,
    enabled: search.length >= 2 || !search,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedUser) {
      onAssign(selectedUser);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-2">
        <label className="text-sm font-medium">Search Employee</label>
        <Input
          placeholder="Type to search (min 2 chars)..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          disabled={isPending}
        />
        {employees && employees.length > 0 && (
          <Select value={selectedUser} onValueChange={setSelectedUser}>
            <SelectTrigger>
              <SelectValue placeholder="Select employee to assign" />
            </SelectTrigger>
            <SelectContent>
              {employees.map((emp: { id: string; first_name: string; last_name: string; employee_id: string; department_name: string | null }) => (
                <SelectItem key={emp.id} value={emp.id}>
                  {emp.first_name} {emp.last_name} ({emp.employee_id}) - {emp.department_name || 'No dept'}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
      {currentAssigneeId && !selectedUser && (
        <p className="text-sm text-muted-foreground">
          Currently assigned. Select a new assignee to reassign.
        </p>
      )}
      <Button type="submit" disabled={isPending || !selectedUser} className="w-full">
        {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {currentAssigneeId ? 'Reassign Task' : 'Assign Task'}
      </Button>
    </form>
  );
}
