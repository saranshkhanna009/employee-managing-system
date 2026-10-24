import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { apiClient } from '../utils/api';
import { LeaveStatus } from '../types';
import { useAuthStore } from '../store/auth';
import { formatDate, cn } from '../utils/helpers';
import { Calendar, Clock, User, ArrowLeft, Loader2, AlertCircle, CheckCircle, XCircle } from 'lucide-react';
import { toast } from 'sonner';

export function LeaveDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, hasRole } = useAuthStore();
  const isManagerOrAbove = hasRole('manager', 'admin', 'super_admin');

  const { data: leave, isLoading } = useQuery({
    queryKey: ['leave', id],
    queryFn: () => apiClient.getLeave(id!),
    enabled: !!id,
  });

  const reviewMutation = useMutation({
    mutationFn: (data: { status: LeaveStatus; review_notes?: string }) => apiClient.reviewLeave(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leave', id] });
      queryClient.invalidateQueries({ queryKey: ['leaves'] });
      queryClient.invalidateQueries({ queryKey: ['leave-balance'] });
      toast.success('Leave request reviewed');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const cancelMutation = useMutation({
    mutationFn: () => apiClient.cancelLeave(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leave', id] });
      queryClient.invalidateQueries({ queryKey: ['leaves'] });
      queryClient.invalidateQueries({ queryKey: ['leave-balance'] });
      toast.success('Leave request cancelled');
      navigate('/leaves');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  if (!id) return null;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" onClick={() => navigate('/leaves')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <h1 className="text-3xl font-bold tracking-tight">Leave Request</h1>
        </div>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse bg-muted rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (!leave?.data) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" onClick={() => navigate('/leaves')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <h1 className="text-3xl font-bold tracking-tight">Leave Request</h1>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <AlertCircle className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">Leave Request Not Found</h2>
            <p className="text-muted-foreground mb-4">This leave request may have been deleted or you don't have permission to view it.</p>
            <Button onClick={() => navigate('/leaves')}>Back to Leave Requests</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const leaveData = leave.data;

  const getStatusIcon = (status: LeaveStatus) => {
    switch (status) {
      case 'approved': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'rejected': return <XCircle className="h-4 w-4 text-red-500" />;
      case 'pending': return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'cancelled': return <XCircle className="h-4 w-4 text-gray-500" />;
      default: return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" onClick={() => navigate('/leaves')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Leave Request Details</h1>
          <p className="text-muted-foreground">Review and manage this leave request</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          {/* Leave Info Card */}
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="capitalize">{leaveData.leave_type.replace('_', ' ')} Leave</CardTitle>
                  <p className="text-muted-foreground">
                    {formatDate(leaveData.start_date)} - {formatDate(leaveData.end_date)} ({leaveData.duration_days} days)
                  </p>
                </div>
                <Badge variant="status" status={leaveData.status} className="text-base px-3 py-1">
                  {getStatusIcon(leaveData.status)}
                  <span className="ml-1 capitalize">{leaveData.status}</span>
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Start Date</label>
                  <p className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    {formatDate(leaveData.start_date)}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">End Date</label>
                  <p className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    {formatDate(leaveData.end_date)}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Duration</label>
                  <p className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    {leaveData.duration_days} days
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Requested On</label>
                  <p>{formatDate(leaveData.created_at)}</p>
                </div>
              </div>

              {leaveData.reason && (
                <div className="pt-4 border-t">
                  <label className="text-sm font-medium text-muted-foreground">Reason</label>
                  <p className="mt-1 whitespace-pre-wrap">{leaveData.reason}</p>
                </div>
              )}

              {leaveData.review_notes && (
                <div className="pt-4 border-t bg-muted/50 rounded-lg p-4">
                  <label className="text-sm font-medium text-muted-foreground">Review Notes</label>
                  <p className="mt-1">{leaveData.review_notes}</p>
                </div>
              )}

              {leaveData.reviewed_by_name && (
                <div className="pt-4 border-t flex items-center gap-3">
                  <User className="h-8 w-8 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">Reviewed by {leaveData.reviewed_by_name}</p>
                    <p className="text-sm text-muted-foreground">{leaveData.reviewed_at ? formatDate(leaveData.reviewed_at) : ''}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Employee Info Card */}
          <Card>
            <CardHeader>
              <CardTitle>Employee Information</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium text-muted-foreground">Employee ID</label>
                <p>{leaveData.employee_id}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Name</label>
                <p>{leaveData.employee_name}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Department</label>
                <p>{leaveData.department_name || 'Not assigned'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Email</label>
                <p>{leaveData.employee_email}</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          {/* Actions Card */}
          <Card>
            <CardHeader>
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {leaveData.status === 'pending' && isManagerOrAbove && (
                <>
                  <Button className="w-full" onClick={() => reviewMutation.mutate({ status: 'approved' })} disabled={reviewMutation.isPending}>
                    <CheckCircle className="mr-2 h-4 w-4" />
                    {reviewMutation.isPending ? 'Approving...' : 'Approve'}
                  </Button>
                  <Button className="w-full" variant="destructive" onClick={() => {
                    const notes = prompt('Rejection reason (optional):');
                    if (notes !== null) reviewMutation.mutate({ status: 'rejected', review_notes: notes });
                  }} disabled={reviewMutation.isPending}>
                    <XCircle className="mr-2 h-4 w-4" />
                    {reviewMutation.isPending ? 'Rejecting...' : 'Reject'}
                  </Button>
                </>
              )}

              {leaveData.employee_id === user?.id && leaveData.status === 'pending' && (
                <Button className="w-full" variant="outline" onClick={() => {
                  if (confirm('Are you sure you want to cancel this leave request?')) {
                    cancelMutation.mutate();
                  }
                }} disabled={cancelMutation.isPending}>
                  <Loader2 className={cn(cancelMutation.isPending && 'animate-spin', 'mr-2 h-4 w-4')} />
                  {cancelMutation.isPending ? 'Cancelling...' : 'Cancel Request'}
                </Button>
              )}

              {leaveData.status !== 'pending' && (
                <p className="text-sm text-muted-foreground text-center">
                  This request has been {leaveData.status}. No further actions available.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Leave Balance Card */}
          {leaveData.employee_id === user?.id && (
            <Card>
              <CardHeader>
                <CardTitle>Your Leave Balance</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  View your remaining leave balance for this year.
                </p>
                <Button variant="outline" className="w-full mt-4" onClick={() => navigate('/leaves')}>
                  View Full Balance
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
