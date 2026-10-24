import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/Tabs';
import { Label } from '../components/ui/Label';
import { Separator } from '../components/ui/Separator';
import { apiClient } from '../utils/api';
import { Employee, SessionInfo } from '../types';
import { useAuthStore } from '../store/auth';
import { formatDate } from '../utils/helpers';
import { User, Shield, Key, Loader2, Eye, EyeOff, Download, Trash2, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

export function SettingsPage() {
  const { user, updateProfile, logout } = useAuthStore();
  const queryClient = useQueryClient();

  const [profileForm, setProfileForm] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    phone: user?.phone || '',
  });

  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });

  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const { data: sessions } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => apiClient.getSessions(),
  });

  const updateProfileMutation = useMutation({
    mutationFn: (data: Partial<Employee>) => apiClient.updateProfile(data),
    onSuccess: (updated) => {
      updateProfile(updated.data);
      toast.success('Profile updated');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const changePasswordMutation = useMutation({
    mutationFn: (data: { current_password: string; new_password: string; confirm_password: string }) => apiClient.changePassword(data),
    onSuccess: () => {
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
      toast.success('Password changed. Please log in again.');
      logout();
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const revokeSessionMutation = useMutation({
    mutationFn: (sessionId: string) => apiClient.revokeSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      toast.success('Session revoked');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const revokeAllSessionsMutation = useMutation({
    mutationFn: () => apiClient.revokeAllSessions(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      toast.success('All other sessions revoked');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const exportDataMutation = useMutation({
    mutationFn: () => apiClient.exportMyData(),
    onSuccess: (data) => {
      const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `employee-data-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Data exported successfully');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteAccountMutation = useMutation({
    mutationFn: () => apiClient.deleteMyAccount(),
    onSuccess: () => {
      toast.success('Account deleted');
      logout();
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const getPasswordStrength = (pwd: string) => {
    let strength = 0;
    if (pwd.length >= 12) strength++;
    if (/[A-Z]/.test(pwd)) strength++;
    if (/[a-z]/.test(pwd)) strength++;
    if (/[0-9]/.test(pwd)) strength++;
    if (/[^A-Za-z0-9]/.test(pwd)) strength++;
    return strength;
  };

  const strength = getPasswordStrength(passwordForm.new_password);
  const strengthLabels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
  const strengthColors = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-lime-500', 'bg-green-500'];

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">Manage your account settings and preferences</p>
      </div>

      <Tabs defaultValue="profile" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
          <TabsTrigger value="sessions">Sessions</TabsTrigger>
          <TabsTrigger value="privacy">Privacy</TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="profile" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
              <CardDescription>Update your personal information</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center gap-4">
                <div className="h-20 w-20 rounded-full bg-primary/10 flex items-center justify-center">
                  <User className="h-10 w-10 text-primary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">{user?.first_name} {user?.last_name}</h3>
                  <p className="text-muted-foreground">{user?.employee_id}</p>
                  <p className="text-sm text-muted-foreground">{user?.email}</p>
                </div>
              </div>

              <Separator />

              <div className="grid gap-4 md:grid-cols-2">
                <div className="grid gap-2">
                  <Label htmlFor="first_name">First Name</Label>
                  <Input
                    id="first_name"
                    value={profileForm.first_name}
                    onChange={(e) => setProfileForm({ ...profileForm, first_name: e.target.value })}
                    disabled={updateProfileMutation.isPending}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="last_name">Last Name</Label>
                  <Input
                    id="last_name"
                    value={profileForm.last_name}
                    onChange={(e) => setProfileForm({ ...profileForm, last_name: e.target.value })}
                    disabled={updateProfileMutation.isPending}
                  />
                </div>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="phone">Phone Number</Label>
                <Input
                  id="phone"
                  type="tel"
                  value={profileForm.phone}
                  onChange={(e) => setProfileForm({ ...profileForm, phone: e.target.value })}
                  disabled={updateProfileMutation.isPending}
                />
              </div>

              <div className="grid gap-2 text-sm text-muted-foreground">
                <div>Email: <span className="font-medium text-foreground">{user?.email}</span> (cannot be changed)</div>
                <div>Employee ID: <span className="font-medium text-foreground">{user?.employee_id}</span> (cannot be changed)</div>
                <div>Role: <span className="font-medium text-foreground capitalize">{user?.role}</span></div>
                <div>Department: <span className="font-medium text-foreground">{user?.department_name || 'Not assigned'}</span></div>
                <div>Member since: <span className="font-medium text-foreground">{user?.created_at ? formatDate(user.created_at) : 'Unknown'}</span></div>
              </div>

              <Button onClick={() => updateProfileMutation.mutate(profileForm)} disabled={updateProfileMutation.isPending}>
                {updateProfileMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Save Changes
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-4 w-4" />
                Security Settings
              </CardTitle>
              <CardDescription>Manage your password and security settings</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="current_password">Current Password</Label>
                  <div className="relative">
                    <Input
                      id="current_password"
                      type={showCurrentPassword ? 'text' : 'password'}
                      value={passwordForm.current_password}
                      onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                      disabled={changePasswordMutation.isPending}
                    />
                    <button
                      type="button"
                      onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                      className="absolute right-3 top-[38px] text-muted-foreground hover:text-foreground"
                    >
                      {showCurrentPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                    </button>
                  </div>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="new_password">New Password</Label>
                  <div className="relative">
                    <Input
                      id="new_password"
                      type={showNewPassword ? 'text' : 'password'}
                      value={passwordForm.new_password}
                      onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                      disabled={changePasswordMutation.isPending}
                      minLength={12}
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute right-3 top-[38px] text-muted-foreground hover:text-foreground"
                    >
                      {showNewPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                    </button>
                  </div>
                  {passwordForm.new_password && (
                    <div className="mt-2">
                      <div className="flex gap-1 h-2">
                        {[1, 2, 3, 4, 5].map((level) => (
                          <div
                            key={level}
                            className={`flex-1 rounded ${level <= strength ? strengthColors[level - 1] : 'bg-muted'}`}
                          />
                        ))}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">Strength: {strengthLabels[strength - 1] || 'Very Weak'}</p>
                    </div>
                  )}
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="confirm_password">Confirm New Password</Label>
                  <div className="relative">
                    <Input
                      id="confirm_password"
                      type={showConfirmPassword ? 'text' : 'password'}
                      value={passwordForm.confirm_password}
                      onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                      disabled={changePasswordMutation.isPending}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-[38px] text-muted-foreground hover:text-foreground"
                    >
                      {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                    </button>
                  </div>
                  {passwordForm.confirm_password && passwordForm.new_password !== passwordForm.confirm_password && (
                    <p className="text-sm text-destructive">Passwords do not match</p>
                  )}
                </div>
              </div>

              <Button
                onClick={() => {
                  if (passwordForm.new_password !== passwordForm.confirm_password) {
                    toast.error('Passwords do not match');
                    return;
                  }
                  if (passwordForm.new_password.length < 12) {
                    toast.error('Password must be at least 12 characters');
                    return;
                  }
                  changePasswordMutation.mutate({
                    current_password: passwordForm.current_password,
                    new_password: passwordForm.new_password,
                    confirm_password: passwordForm.confirm_password,
                  });
                }}
                disabled={changePasswordMutation.isPending || passwordForm.new_password !== passwordForm.confirm_password || passwordForm.new_password.length < 12}
              >
                {changePasswordMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Change Password
              </Button>
            </CardContent>
          </Card>

          <Card className="border-destructive/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="h-4 w-4" />
                Danger Zone
              </CardTitle>
              <CardDescription>Irreversible actions</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg bg-destructive/5">
                <div>
                  <p className="font-medium">Delete Account</p>
                  <p className="text-sm text-muted-foreground">Permanently delete your account and all associated data. This action cannot be undone.</p>
                </div>
                <Button variant="destructive" onClick={() => {
                  if (confirm('Are you absolutely sure? This will permanently delete your account and all data.')) {
                    deleteAccountMutation.mutate();
                  }
                }} disabled={deleteAccountMutation.isPending}>
                  <Trash2 className="mr-2 h-4 w-4" />
                  {deleteAccountMutation.isPending ? 'Deleting...' : 'Delete Account'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Sessions Tab */}
        <TabsContent value="sessions" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-4 w-4" />
                Active Sessions
              </CardTitle>
              <CardDescription>Manage your active login sessions</CardDescription>
            </CardHeader>
            <CardContent>
              {sessions?.data?.length > 0 ? (
                <div className="space-y-4">
                  {sessions?.data?.map((session: SessionInfo) => (
                    <div key={session.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-4">
                        <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                          <Key className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <p className="font-medium">{session.is_current ? 'Current Session' : 'Other Session'}</p>
                          <p className="text-sm text-muted-foreground">
                            {session.device_fingerprint || 'Unknown device'} • {session.ip_address || 'Unknown IP'}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Created: {formatDate(session.created_at)} • Expires: {formatDate(session.expires_at)}
                          </p>
                        </div>
                      </div>
                      {!session.is_current && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => revokeSessionMutation.mutate(session.id)}
                          disabled={revokeSessionMutation.isPending}
                        >
                          Revoke
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center py-8 text-muted-foreground">No active sessions found</p>
              )}

              <Separator className="my-6" />

              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Revoke All Other Sessions</p>
                  <p className="text-sm text-muted-foreground">Sign out of all other devices and browsers</p>
                </div>
                <Button
                  variant="outline"
                  onClick={() => {
                    if (confirm('This will sign you out of all other devices. Continue?')) {
                      revokeAllSessionsMutation.mutate();
                    }
                  }}
                  disabled={revokeAllSessionsMutation.isPending}
                >
                  {revokeAllSessionsMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Revoke All Other Sessions
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Privacy Tab */}
        <TabsContent value="privacy" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Download className="h-4 w-4" />
                Data Export
              </CardTitle>
              <CardDescription>Download a copy of all your personal data</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="p-4 border rounded-lg">
                  <h4 className="font-medium mb-2">Your Data</h4>
                  <p className="text-sm text-muted-foreground mb-4">
                    You can download a JSON file containing all your personal data including:
                  </p>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Profile information (name, email, phone, employee ID)</li>
                    <li>Assigned tasks and their status</li>
                    <li>Daily work logs</li>
                    <li>Leave requests and their status</li>
                    <li>Session history (IP addresses, devices)</li>
                  </ul>
                </div>
                <Button onClick={() => exportDataMutation.mutate()} disabled={exportDataMutation.isPending} className="w-full">
                  {exportDataMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {exportDataMutation.isPending ? 'Preparing Export...' : 'Export My Data'}
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Cookie Policy</CardTitle>
              <CardDescription>Information about how we use cookies</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-muted-foreground">
              <div className="prose prose-sm">
                <p>This application uses only essential cookies for session management:</p>
                <ul className="list-disc list-inside space-y-2">
                  <li><strong>Session Cookie (__Host-session):</strong> Secure, HttpOnly, SameSite=Strict cookie that stores your session token. This cookie is required for authentication and cannot be disabled.</li>
                  <li><strong>No Tracking Cookies:</strong> We do not use analytics cookies, advertising cookies, or any third-party tracking cookies.</li>
                  <li><strong>No LocalStorage Tracking:</strong> We do not store tracking data in localStorage or sessionStorage beyond your UI preferences (theme, sidebar state).</li>
                </ul>
                <p className="mt-4">The session cookie:</p>
                <ul className="list-disc list-inside space-y-1 ml-4">
                  <li>Is encrypted and signed</li>
                  <li>Expires after 24 hours (or 30 days if "Remember me" is checked)</li>
                  <li>Is automatically deleted on logout</li>
                  <li>Cannot be accessed by JavaScript (HttpOnly)</li>
                  <li>Is only sent over HTTPS (Secure)</li>
                  <li>Is not sent with cross-site requests (SameSite=Strict)</li>
                </ul>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="h-4 w-4" />
                Data Retention & Deletion
              </CardTitle>
              <CardDescription>Your rights under privacy regulations</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-muted-foreground">
              <div className="prose prose-sm">
                <p>Under GDPR and similar regulations, you have the right to:</p>
                <ul className="list-disc list-inside space-y-2">
                  <li>Access your personal data (use "Export My Data" above)</li>
                  <li>Request correction of inaccurate data</li>
                  <li>Request deletion of your data (use "Delete Account" in Security tab)</li>
                  <li>Restrict processing of your data</li>
                  <li>Data portability</li>
                </ul>
                <p className="mt-4">When you delete your account:</p>
                <ul className="list-disc list-inside space-y-1 ml-4">
                  <li>Your personal data is permanently removed</li>
                  <li>Your tasks are reassigned or archived</li>
                  <li>Your daily logs are anonymized</li>
                  <li>Your leave requests are cancelled</li>
                  <li>Audit logs are retained for compliance (with personal identifiers removed)</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
