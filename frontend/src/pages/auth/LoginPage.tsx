import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../../components/ui/Card';
import { Label } from '../../components/ui/Label';
import { useAuthStore } from '../../store/auth';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const loginSchema = z.object({
  employee_id: z.string().min(1, 'Employee ID is required'),
  password: z.string().min(1, 'Password is required'),
  remember_me: z.boolean().default(false),
});

type LoginForm = z.infer<typeof loginSchema>;

export function LoginPage() {
  const navigate = useNavigate();
  const { login, isLoading } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { remember_me: false },
  });

  const onSubmit = async (data: LoginForm) => {
    setError(null);
    try {
      await login(data.employee_id, data.password, data.remember_me);
      toast.success('Welcome back!');
      navigate('/dashboard');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
      toast.error(message);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/50 px-4 py-12">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">Sign in</CardTitle>
          <CardDescription className="text-center">
            Enter your Employee ID and password to access your account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Employee ID"
              placeholder="EMP-COMP-0001"
              {...register('employee_id')}
              error={errors.employee_id?.message}
              disabled={isLoading}
              autoComplete="username"
            />

            <div className="relative">
              <Label htmlFor="password">Password</Label>
              <div className="relative mt-1.5">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  {...register('password')}
                  error={errors.password?.message}
                  disabled={isLoading}
                  autoComplete="current-password"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-[38px] text-muted-foreground hover:text-foreground"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  {...register('remember_me')}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                  disabled={isLoading}
                />
                <span className="text-sm">Remember me for 30 days</span>
              </label>
              <span className="text-sm text-muted-foreground" title="Ask an administrator to reset your password">
                Contact an administrator to reset your password
              </span>
            </div>

            {error && (
              <div className="text-sm text-destructive text-center" role="alert">
                {error}
              </div>
            )}

            <Button type="submit" className="w-full" disabled={isLoading} size="lg">
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Sign in
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-muted-foreground">
            Don't have an account?{' '}
            <Link to="/register" className="text-primary hover:underline font-medium">
              Register your company
            </Link>
          </div>
        </CardContent>
        <CardFooter className="flex justify-center text-xs text-muted-foreground">
          <p>Employee Tracker v1.0.0 - Secure &amp; Encrypted</p>
        </CardFooter>
      </Card>
    </div>
  );
}
