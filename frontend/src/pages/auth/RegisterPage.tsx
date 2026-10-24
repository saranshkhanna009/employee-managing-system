import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../../components/ui/Card';
import { Label } from '../../components/ui/Label';
import { apiClient } from '../../utils/api';
import { Loader2, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';

const registerSchema = z.object({
  company_name: z.string().min(2, 'Company name must be at least 2 characters'),
  company_slug: z.string().min(2, 'Slug must be at least 2 characters').regex(/^[a-z0-9-]+$/, 'Slug can only contain lowercase letters, numbers, and hyphens'),
  admin_email: z.string().email('Invalid email address'),
  admin_password: z.string().min(12, 'Password must be at least 12 characters'),
  admin_confirm_password: z.string(),
  admin_first_name: z.string().min(1, 'First name is required'),
  admin_last_name: z.string().min(1, 'Last name is required'),
  admin_phone: z.string().optional(),
}).refine((data) => data.admin_password === data.admin_confirm_password, {
  message: 'Passwords do not match',
  path: ['admin_confirm_password'],
});

type RegisterForm = z.infer<typeof registerSchema>;

export function RegisterPage() {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  const password = watch('admin_password');

  const getPasswordStrength = (pwd: string) => {
    let strength = 0;
    if (pwd.length >= 12) strength++;
    if (/[A-Z]/.test(pwd)) strength++;
    if (/[a-z]/.test(pwd)) strength++;
    if (/[0-9]/.test(pwd)) strength++;
    if (/[^A-Za-z0-9]/.test(pwd)) strength++;
    return strength;
  };

  const strength = getPasswordStrength(password);
  const strengthLabels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
  const strengthColors = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-lime-500', 'bg-green-500'];

  const onSubmit = async (data: RegisterForm) => {
    setIsLoading(true);
    try {
      await apiClient.registerCompany({
        company_name: data.company_name,
        company_slug: data.company_slug,
        admin_email: data.admin_email,
        admin_password: data.admin_password,
        admin_first_name: data.admin_first_name,
        admin_last_name: data.admin_last_name,
        admin_phone: data.admin_phone,
      });
      toast.success('Company registered successfully!');
      navigate('/login');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Registration failed';
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/50 px-4 py-12">
      <Card className="w-full max-w-2xl">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">Register Company</CardTitle>
          <CardDescription className="text-center">
            Create your company account and super admin user
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <Label htmlFor="company_name">Company Name</Label>
                <Input
                  id="company_name"
                  placeholder="Acme Corporation"
                  {...register('company_name')}
                  error={errors.company_name?.message}
                  disabled={isLoading}
                />
              </div>

              <div>
                <Label htmlFor="company_slug">Company Slug (URL)</Label>
                <Input
                  id="company_slug"
                  placeholder="acme-corp"
                  {...register('company_slug')}
                  error={errors.company_slug?.message}
                  disabled={isLoading}
                />
                <p className="text-xs text-muted-foreground mt-1">Used for your company URL: app.example.com/{watch('company_slug')}</p>
              </div>
            </div>

            <div className="border-t pt-6">
              <h3 className="text-lg font-semibold mb-4">Super Admin Account</h3>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label htmlFor="admin_first_name">First Name</Label>
                  <Input
                    id="admin_first_name"
                    placeholder="John"
                    {...register('admin_first_name')}
                    error={errors.admin_first_name?.message}
                    disabled={isLoading}
                  />
                </div>
                <div>
                  <Label htmlFor="admin_last_name">Last Name</Label>
                  <Input
                    id="admin_last_name"
                    placeholder="Doe"
                    {...register('admin_last_name')}
                    error={errors.admin_last_name?.message}
                    disabled={isLoading}
                  />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2 mt-4">
                <div>
                  <Label htmlFor="admin_email">Email</Label>
                <Input
                  id="admin_email"
                  type="email"
                  placeholder="admin@company.com"
                  {...register('admin_email')}
                  error={errors.admin_email?.message}
                  disabled={isLoading}
                />
              </div>

              <div>
                <Label htmlFor="admin_phone">Phone (Optional)</Label>
                <Input
                  id="admin_phone"
                  type="tel"
                  placeholder="+1 (555) 123-4567"
                  {...register('admin_phone')}
                  disabled={isLoading}
                />
              </div>

              <div className="md:col-span-2">
                <Label htmlFor="admin_password">Password</Label>
                <div className="relative">
                  <Input
                    id="admin_password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••••••"
                    {...register('admin_password')}
                    error={errors.admin_password?.message}
                    disabled={isLoading}
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-[38px] text-muted-foreground hover:text-foreground"
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
                {password && (
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

                <Label htmlFor="admin_confirm_password">Confirm Password</Label>
                <Input
                  id="admin_confirm_password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••••••"
                  {...register('admin_confirm_password')}
                  error={errors.admin_confirm_password?.message}
                  disabled={isLoading}
                />
              </div>
            </div>
          </div>

          <Button type="submit" className="w-full" disabled={isLoading} size="lg">
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Register Company
          </Button>

            <p className="text-center text-sm text-muted-foreground mt-4">
              Already have an account?{' '}
              <Link to="/login" className="text-primary hover:underline font-medium">
                Sign in
              </Link>
            </p>
          </form>
        </CardContent>
        <CardFooter className="flex justify-center text-xs text-muted-foreground">
          <p>By registering, you agree to our Terms of Service and Privacy Policy</p>
        </CardFooter>
      </Card>
    </div>
  );
}