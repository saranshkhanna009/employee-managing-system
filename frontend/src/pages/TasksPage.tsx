import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
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
import { Task, TaskStatus, TaskPriority } from '../types';
import { useAuthStore } from '../store/auth';
import { formatDate, cn } from '../utils/helpers';
import {
  Plus,
  Search,
  MoreVertical,
  Edit,
  Trash2,
  Calendar,
  User,
  Loader2,
} from 'lucide-react';
import { toast } from 'sonner';
import { TaskCreateInput } from '../utils/api';

export function TasksPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { hasRole } = useAuthStore();
  const isManagerOrAbove = hasRole('manager', 'admin', 'super_admin');

  const [filters, setFilters] = useState({
    status: '',
    priority: '',
    search: '',
    department_id: searchParams.get('department_id') || '',
    assignee_id: searchParams.get('assignee_id') || searchParams.get('assigned_to') || '',
    page: 1,
    page_size: 20,
  });

  const { data: tasksData, isLoading } = useQuery({
    queryKey: ['tasks', filters],
    queryFn: () => apiClient.getTasks(filters),
  });

  const createMutation = useMutation({
    mutationFn: (data: TaskCreateInput) => apiClient.createTask(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success('Task created successfully');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: TaskStatus }) => apiClient.updateTaskStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success('Task status updated');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteTask(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success('Task deleted');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const handleCreateTask = (data: TaskCreateInput) => {
    createMutation.mutate(data);
  };

  const handleUpdateStatus = (task: Task, status: TaskStatus) => {
    updateStatusMutation.mutate({ id: task.id, status });
  };

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this task?')) {
      deleteMutation.mutate(id);
    }
  };

  const tasks = tasksData?.data.items || [];
  const total = tasksData?.data.total || 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Tasks</h1>
          <p className="text-muted-foreground">Manage and track your tasks</p>
        </div>
        {isManagerOrAbove && (
          <Dialog>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create Task
              </Button>
            </DialogTrigger>
            <DialogContent>
              <TaskForm onSubmit={handleCreateTask} />
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
                placeholder="Search tasks..."
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
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="in_review">In Review</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="blocked">Blocked</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filters.priority} onValueChange={(value) => setFilters({ ...filters, priority: value === '__all__' ? '' : value, page: 1 })}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="All Priorities" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All Priorities</SelectItem>
                <SelectItem value="low">Low</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="urgent">Urgent</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Tasks Table */}
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
                      <TableHead>Task</TableHead>
                      <TableHead>Assignee</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Priority</TableHead>
                      <TableHead>Due Date</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tasks.length > 0 ? (
                      tasks.map((task: Task) => (
                        <TableRow key={task.id}>
                          <TableCell>
                            <Link to={`/tasks/${task.id}`} className="font-medium hover:underline">
                              {task.title}
                            </Link>
                            <p className="text-sm text-muted-foreground truncate max-w-xs">
                              {task.department_name || 'No department'}
                            </p>
                          </TableCell>
                          <TableCell>
                            {task.assigned_to_name ? (
                              <div className="flex items-center gap-2">
                                <User className="h-4 w-4 text-muted-foreground" />
                                <span>{task.assigned_to_name}</span>
                              </div>
                            ) : (
                              <span className="text-muted-foreground">Unassigned</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <Badge variant="status" status={task.status}>
                              {task.status.replace('_', ' ')}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant="priority" priority={task.priority}>
                              {task.priority}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {task.due_date ? (
                              <span className={cn(task.is_overdue && 'text-destructive')}>
                                <Calendar className="inline h-3 w-3 mr-1" />
                                {formatDate(task.due_date)}
                                {task.is_overdue && ' (Overdue)'}
                              </span>
                            ) : (
                              <span className="text-muted-foreground">No due date</span>
                            )}
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
                                  <Link to={`/tasks/${task.id}`}>View Details</Link>
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onClick={() => handleUpdateStatus(task, 'in_progress')}>
                                  Mark In Progress
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => handleUpdateStatus(task, 'completed')}>
                                  Mark Complete
                                </DropdownMenuItem>
                                {isManagerOrAbove && (
                                  <>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem onClick={() => navigate(`/tasks/${task.id}`)}>
                                      <Edit className="mr-2 h-4 w-4" />
                                      Edit
                                    </DropdownMenuItem>
                                    <DropdownMenuItem
                                      onClick={() => handleDelete(task.id)}
                                      className="text-destructive focus:text-destructive"
                                    >
                                      <Trash2 className="mr-2 h-4 w-4" />
                                      Delete
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
                          No tasks found
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
                    {Math.min(filters.page * filters.page_size, total)} of {total} tasks
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

function TaskForm({ onSubmit }: { onSubmit: (data: TaskCreateInput) => void }) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);
    const formData = new FormData(e.currentTarget);
    const data = {
      title: formData.get('title') as string,
      description: formData.get('description') as string,
      department_id: formData.get('department_id') as string || undefined,
      assigned_to_id: formData.get('assigned_to_id') as string || undefined,
      priority: formData.get('priority') as TaskPriority,
      due_date: formData.get('due_date') as string || undefined,
      estimated_hours: formData.get('estimated_hours') ? parseFloat(formData.get('estimated_hours') as string) : undefined,
    };
    await onSubmit(data);
    setIsSubmitting(false);
  };

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle>Create New Task</DialogTitle>
      </DialogHeader>
      <div className="grid gap-4 py-4">
        <div className="grid gap-2">
          <label htmlFor="title" className="text-sm font-medium">Title *</label>
          <Input id="title" name="title" required placeholder="Enter task title" />
        </div>
        <div className="grid gap-2">
          <label htmlFor="description" className="text-sm font-medium">Description</label>
          <textarea id="description" name="description" className="min-h-[100px] p-2 border rounded" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
            <label htmlFor="priority" className="text-sm font-medium">Priority</label>
            <Select name="priority" defaultValue="medium">
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Low</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="urgent">Urgent</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <label htmlFor="due_date" className="text-sm font-medium">Due Date</label>
            <Input id="due_date" name="due_date" type="date" />
          </div>
        </div>
        <div className="grid gap-2">
          <label htmlFor="estimated_hours" className="text-sm font-medium">Estimated Hours</label>
          <Input id="estimated_hours" name="estimated_hours" type="number" step="0.5" min="0" placeholder="e.g., 8" />
        </div>
      </div>
      <DialogFooter>
        <DialogClose asChild>
          <Button type="button" variant="outline">Cancel</Button>
        </DialogClose>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Create Task
        </Button>
      </DialogFooter>
    </form>
  );
}
