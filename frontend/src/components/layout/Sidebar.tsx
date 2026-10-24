import { Link, NavLink } from 'react-router-dom';
import { useAuthStore } from '../../store/auth';
import { cn } from '../../utils/helpers';
import {
  LayoutDashboard,
  Users,
  ClipboardList,
  Calendar,
  FileText,
  Settings,
  LogOut,
  Building2,
  Shield,
  BarChart3,
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Avatar } from '../ui/Avatar';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '../ui/DropdownMenu';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, roles: ['employee', 'manager', 'admin', 'super_admin'] },
  { name: 'My Tasks', href: '/tasks', icon: ClipboardList, roles: ['employee', 'manager', 'admin', 'super_admin'] },
  { name: 'Daily Logs', href: '/daily-logs', icon: Calendar, roles: ['employee', 'manager', 'admin', 'super_admin'] },
  { name: 'Leave Requests', href: '/leaves', icon: FileText, roles: ['employee', 'manager', 'admin', 'super_admin'] },
  { name: 'Team', href: '/team', icon: Users, roles: ['manager', 'admin', 'super_admin'] },
  { name: 'Departments', href: '/departments', icon: Building2, roles: ['admin', 'super_admin'] },
  { name: 'Employees', href: '/employees', icon: Users, roles: ['admin', 'super_admin'] },
  { name: 'Audit Logs', href: '/audit', icon: Shield, roles: ['admin', 'super_admin'] },
  { name: 'Analytics', href: '/analytics', icon: BarChart3, roles: ['admin', 'super_admin'] },
  { name: 'Settings', href: '/settings', icon: Settings, roles: ['employee', 'manager', 'admin', 'super_admin'] },
];

export function Sidebar() {
  const { user, logout, hasRole } = useAuthStore();

  const filteredNav = navigation.filter((item) =>
    user && item.roles.some((role) => hasRole(role))
  );

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r bg-card transition-all duration-200">
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center justify-between border-b px-4">
          <Link to="/dashboard" className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-sm">ET</span>
            </div>
            <span className="font-semibold text-lg">EmployeeTracker</span>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-4 overflow-y-auto" aria-label="Main navigation">
          {filteredNav.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive: active }) =>
                  cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    active
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  )
                }
              >
                <Icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
                {item.name}
              </NavLink>
            );
          })}
        </nav>

        {/* User Profile */}
        <div className="border-t p-4">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="w-full justify-start gap-3 h-auto py-2" aria-label="User menu">
                <Avatar
                  name={user?.full_name}
                  size="sm"
                  className="bg-primary/10 text-primary"
                />
                <div className="flex-1 text-left min-w-0">
                  <p className="text-sm font-medium truncate">{user?.full_name}</p>
                  <p className="text-xs text-muted-foreground truncate">{user?.employee_id}</p>
                </div>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <div className="px-2 py-1">
                <p className="text-xs text-muted-foreground">Signed in as</p>
                <p className="text-sm font-medium">{user?.email}</p>
                <p className="text-xs text-muted-foreground capitalize">{user?.role.replace('_', ' ')}</p>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link to="/settings" className="w-full">Settings</Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => logout()}
                className="text-destructive focus:text-destructive"
              >
                <LogOut className="mr-2 h-4 w-4" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </aside>
  );
}
