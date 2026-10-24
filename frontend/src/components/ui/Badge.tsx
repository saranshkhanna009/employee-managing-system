import { HTMLAttributes, forwardRef } from 'react';
import { cn } from '../../utils/helpers';
import { getStatusColor, getPriorityColor, getRoleColor } from '../../utils/helpers';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'status' | 'priority' | 'role';
  status?: string;
  priority?: string;
  role?: string;
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', status, priority, role, ...props }, ref) => {
    let variantClass = '';

    switch (variant) {
      case 'status':
        variantClass = status ? getStatusColor(status) : '';
        break;
      case 'priority':
        variantClass = priority ? getPriorityColor(priority) : '';
        break;
      case 'role':
        variantClass = role ? getRoleColor(role) : '';
        break;
      case 'default':
        variantClass = 'bg-primary text-primary-foreground hover:bg-primary/80';
        break;
      case 'secondary':
        variantClass = 'bg-secondary text-secondary-foreground hover:bg-secondary/80';
        break;
      case 'destructive':
        variantClass = 'bg-destructive text-destructive-foreground hover:bg-destructive/80';
        break;
      case 'outline':
        variantClass = 'text-foreground border border-input';
        break;
    }

    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
          variantClass,
          className
        )}
        {...props}
      />
    );
  }
);

Badge.displayName = 'Badge';