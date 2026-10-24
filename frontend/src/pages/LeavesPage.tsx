import { useState } from 'react';
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
import { apiClient } from '../utils/api';
import { LeaveRequest, LeaveType, LeaveStatus, LeaveBalance } from '../types';
import { useAuthStore } from '../store/auth';
import { formatDate } from '../utils/helpers';
import { Plus, Calendar, Trash2, Loader2, MoreVertical } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '../components/ui/DropdownMenu';
import { toast } from 'sonner';

export function LeavesPage() {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const { user } = useAuthStore();

  const [filters, setFilters] = useState({
    status: '',
    leave_type: '',
    employee_id: searchParams.get('employee_id') || '',
    page: 1,
    page_size: 20,
  });

  const { data: leavesData, isLoading } = useQuery({
    queryKey: ['leaves', filters],
    queryFn: () => apiClient.getLeaves(filters),
  });

  const { data: balance } = useQuery({
    queryKey: ['leave-balance'],
    queryFn: () => apiClient.getLeaveBalance(),
  });

  const createMutation = useMutation({
    mutationFn: (data: { leave_type: string; start_date: string; end_date: string; reason?: string }) => apiClient.createLeave(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leaves'] });
      queryClient.invalidateQueries({ queryKey: ['leave-balance'] });
      toast.success('Leave request submitted');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const reviewMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { status: LeaveStatus; review_notes?: string } }) =>
      apiClient.reviewLeave(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leaves'] });
      queryClient.invalidateQueries({ queryKey: ['leave-balance'] });
      toast.success('Leave request reviewed');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => apiClient.cancelLeave(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leaves'] });
      queryClient.invalidateQueries({ queryKey: ['leave-balance'] });
      toast.success('Leave request cancelled');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const leaves = leavesData?.data.items || [];
  const total = leavesData?.data.total || 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Leave Requests</h1>
          <p className="text-muted-foreground">Manage your leave requests and balance</p>
        </div>
        <Dialog>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Request Leave
            </Button>
          </DialogTrigger>
          <DialogContent>
            <LeaveForm onSubmit={createMutation.mutate} />
          </DialogContent>
        </Dialog>
      </div>

      {/* Leave Balance */}
      {balance && (
        <Card>
          <CardHeader>
          <CardTitle>Leave Balance (Year: {balance.data.year})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {balance.data.balances.map((b: LeaveBalance) => (
                <div key={b.leave_type} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium capitalize">{b.leave_type.replace('_', ' ')}</span>
                    <Badge variant={b.remaining > 0 ? 'default' : 'destructive'}>
                      {b.remaining} days left
                    </Badge>
                  </div>
                  <div className="text-sm text-muted-foreground space-y-1">
                    <div>Allocated: <span className="font-medium">{b.allocated}</span></div>
                    <div>Used: <span className="font-medium">{b.used}</span></div>
                    {b.pending > 0 && <div>Pending: <span className="font-medium text-yellow-600">{b.pending}</span></div>}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <Select value={filters.status} onValueChange={(value) => setFilters({ ...filters, status: value === '__all__' ? '' : value, page: 1 })}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All Statuses</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filters.leave_type} onValueChange={(value) => setFilters({ ...filters, leave_type: value === '__all__' ? '' : value, page: 1 })}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All Types</SelectItem>
                <SelectItem value="sick">Sick</SelectItem>
                <SelectItem value="vacation">Vacation</SelectItem>
                <SelectItem value="personal">Personal</SelectItem>
                <SelectItem value="emergency">Emergency</SelectItem>
                <SelectItem value="maternity">Maternity</SelectItem>
                <SelectItem value="paternity">Paternity</SelectItem>
                <SelectItem value="bereavement">Bereavement</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Leaves Table */}
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
                      <TableHead>Type</TableHead>
                      <TableHead>Dates</TableHead>
                      <TableHead>Duration</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Reviewed By</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {leaves.length > 0 ? (
                      leaves.map((leave: LeaveRequest) => (
                        <TableRow key={leave.id}>
                          <TableCell>
                            <Badge variant="default" className="capitalize">{leave.leave_type.replace('_', ' ')}</Badge>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Calendar className="h-4 w-4 text-muted-foreground" />
                              <span>{formatDate(leave.start_date)} - {formatDate(leave.end_date)}</span>
                            </div>
                          </TableCell>
                          <TableCell>{leave.duration_days} days</TableCell>
                          <TableCell>
                            <Badge variant="status" status={leave.status}>
                              {leave.status}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {leave.reviewed_by_name ? (
                              <div>
                                <p>{leave.reviewed_by_name}</p>
                                <p className="text-xs text-muted-foreground">
                                  {leave.reviewed_at ? formatDate(leave.reviewed_at) : ''}
                                </p>
                              </div>
                            ) : (
                              <span className="text-muted-foreground">-</span>
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
                                  <Link to={`/leaves/${leave.id}`}>View Details</Link>
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                {leave.status === 'pending' && (
                                  <>
                                    <DropdownMenuItem onClick={() => reviewMutation.mutate({ id: leave.id, data: { status: 'approved' } })}>
                                      Approve
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => reviewMutation.mutate({ id: leave.id, data: { status: 'rejected' } })}>
                                      Reject
                                    </DropdownMenuItem>
                                    <DropdownMenuSeparator />
                                  </>
                                )}
                                {leave.employee_id === user?.id && leave.status === 'pending' && (
                                  <DropdownMenuItem
                                    onClick={() => cancelMutation.mutate(leave.id)}
                                    className="text-destructive focus:text-destructive"
                                  >
                                    <Trash2 className="mr-2 h-4 w-4" />
                                    Cancel Request
                                  </DropdownMenuItem>
                                )}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                          No leave requests found
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
                    {Math.min(filters.page * filters.page_size, total)} of {total} requests
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

function LeaveForm({ onSubmit }: { onSubmit: (data: { leave_type: LeaveType; start_date: string; end_date: string; reason?: string }) => void }) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);
    const formData = new FormData(e.currentTarget);
    const data = {
      leave_type: formData.get('leave_type') as LeaveType,
      start_date: formData.get('start_date') as string,
      end_date: formData.get('end_date') as string,
      reason: formData.get('reason') as string,
    };
    await onSubmit(data);
    setIsSubmitting(false);
  };

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle>Request Leave</DialogTitle>
      </DialogHeader>
      <div className="grid gap-4 py-4">
        <div className="grid gap-2">
          <label htmlFor="leave_type" className="text-sm font-medium">Leave Type *</label>
          <Select name="leave_type" required>
            <SelectTrigger>
              <SelectValue placeholder="Select leave type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="sick">Sick Leave</SelectItem>
              <SelectItem value="vacation">Vacation</SelectItem>
              <SelectItem value="personal">Personal</SelectItem>
              <SelectItem value="emergency">Emergency</SelectItem>
              <SelectItem value="maternity">Maternity</SelectItem>
              <SelectItem value="paternity">Paternity</SelectItem>
              <SelectItem value="bereavement">Bereavement</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
            <label htmlFor="start_date" className="text-sm font-medium">Start Date *</label>
            <Input id="start_date" name="start_date" type="date" required />
          </div>
          <div className="grid gap-2">
            <label htmlFor="end_date" className="text-sm font-medium">End Date *</label>
            <Input id="end_date" name="end_date" type="date" required />
          </div>
        </div>
        <div className="grid gap-2">
          <label htmlFor="reason" className="text-sm font-medium">Reason</label>
          <Textarea id="reason" name="reason" placeholder="Reason for leave request..." rows={3} />
        </div>
      </div>
      <DialogFooter>
        <DialogClose asChild>
          <Button type="button" variant="outline">Cancel</Button>
        </DialogClose>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Submit Request
        </Button>
      </DialogFooter>
    </form>
  );
}
