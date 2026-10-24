import { describe, expect, it } from 'vitest';
import { calculateDuration, cn, getInitials, getStatusColor, truncate } from './helpers';

describe('frontend helpers', () => {
  it('merges utility classes and preserves the last Tailwind conflict winner', () => {
    expect(cn('px-2 text-sm', 'px-4')).toBe('text-sm px-4');
  });

  it('formats initials and truncates long labels', () => {
    expect(getInitials('Ada Lovelace')).toBe('AL');
    expect(truncate('Employee tracking system', 12)).toBe('Employee ...');
  });

  it('calculates inclusive date ranges and uses a safe fallback status color', () => {
    expect(calculateDuration('2026-10-01', '2026-10-03')).toBe(3);
    expect(getStatusColor('unknown')).toContain('bg-gray-100');
  });
});
