// Frontend component tests with Vitest + jsdom.
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import StatCard from './components/StatCard';
import EmptyState, { ErrorState } from './components/EmptyState';
import Loading, { PageLoader, InlineLoader } from './components/Loading';
import NotFound from './pages/NotFound';
import { severityBadge, statusBadge, formatDate, timeAgo, getInitials, priorityColor } from './utils/helpers';

describe('StatCard', () => {
  it('renders title, value, and subtitle', () => {
    render(<StatCard title="Total Reports" value={42} subtitle="All time" icon="📝" />);
    expect(screen.getByText('Total Reports')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('All time')).toBeInTheDocument();
  });

  it('renders trend when provided', () => {
    render(<StatCard title="Growth" value="10%" trend={5.2} />);
    expect(screen.getByText(/5\.2%/)).toBeInTheDocument();
  });
});

describe('EmptyState', () => {
  it('renders title and message', () => {
    render(<EmptyState title="Nothing here" message="Try again later" />);
    expect(screen.getByText('Nothing here')).toBeInTheDocument();
    expect(screen.getByText('Try again later')).toBeInTheDocument();
  });
});

describe('ErrorState', () => {
  it('renders with default title', () => {
    render(<ErrorState message="Network error" />);
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('Network error')).toBeInTheDocument();
  });
});

describe('Loading', () => {
  it('renders spinner with label', () => {
    render(<Loading label="Please wait" />);
    expect(screen.getByText('Please wait')).toBeInTheDocument();
  });
});

describe('NotFound page', () => {
  it('renders 404 and home link', () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>
    );
    expect(screen.getByText('404')).toBeInTheDocument();
    expect(screen.getByText('Page Not Found')).toBeInTheDocument();
  });
});

describe('helper functions', () => {
  it('severityBadge returns unassessed for null', () => {
    const result = severityBadge(null);
    expect(result.props.children).toBe('Unassessed');
  });

  it('severityBadge returns label for valid severity', () => {
    const result = severityBadge('Critical');
    expect(result.props.children).toBe('Critical');
  });

  it('statusBadge returns null for null', () => {
    expect(statusBadge(null)).toBeNull();
  });

  it('formatDate returns — for null', () => {
    expect(formatDate(null)).toBe('—');
  });

  it('formatDate returns formatted string for valid date', () => {
    const result = formatDate('2026-01-15T10:30:00');
    expect(result).toContain('2026');
    expect(result).toContain('Jan');
  });

  it('timeAgo returns "just now" for recent date', () => {
    const result = timeAgo(new Date());
    expect(result).toBe('just now');
  });

  it('getInitials returns uppercase initials', () => {
    expect(getInitials('Jane Doe')).toBe('JD');
    expect(getInitials('John Ronald Reuel Tolkien')).toBe('JR');
  });

  it('priorityColor returns color classes for score ranges', () => {
    expect(priorityColor(85)).toContain('purple');
    expect(priorityColor(65)).toContain('red');
    expect(priorityColor(45)).toContain('amber');
    expect(priorityColor(25)).toContain('blue');
    expect(priorityColor(10)).toContain('slate');
    expect(priorityColor(null)).toContain('slate');
  });
});
