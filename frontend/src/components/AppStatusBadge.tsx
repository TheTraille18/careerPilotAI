import type { AppStatus } from '../theme/ablackcloud';

const statusStyles: Record<
  AppStatus,
  { label: string; backgroundColor: string; color: string; borderColor: string }
> = {
  Live: {
    label: 'Live',
    backgroundColor: 'rgba(0, 166, 153, 0.92)',
    color: '#ffffff',
    borderColor: 'rgba(0, 166, 153, 1)',
  },
  'In Development': {
    label: 'In Development',
    backgroundColor: 'rgba(126, 200, 255, 0.92)',
    color: '#0a1628',
    borderColor: 'rgba(126, 200, 255, 1)',
  },
  'In Progress': {
    label: 'In Progress',
    backgroundColor: 'rgba(255, 180, 50, 0.92)',
    color: '#1a1400',
    borderColor: 'rgba(255, 200, 80, 1)',
  },
  Beta: {
    label: 'Beta',
    backgroundColor: 'rgba(123, 97, 255, 0.92)',
    color: '#ffffff',
    borderColor: 'rgba(123, 97, 255, 1)',
  },
  Planned: {
    label: 'Planned',
    backgroundColor: 'rgba(80, 80, 80, 0.88)',
    color: '#ffffff',
    borderColor: 'rgba(255, 255, 255, 0.35)',
  },
  POC: {
    label: 'POC',
    backgroundColor: 'rgba(255, 180, 50, 0.92)',
    color: '#1a1400',
    borderColor: 'rgba(255, 200, 80, 1)',
  },
  Maintenance: {
    label: 'Maintenance',
    backgroundColor: 'rgba(255, 140, 60, 0.92)',
    color: '#ffffff',
    borderColor: 'rgba(255, 160, 90, 1)',
  },
  Deprecated: {
    label: 'Deprecated',
    backgroundColor: 'rgba(180, 60, 60, 0.88)',
    color: '#ffffff',
    borderColor: 'rgba(255, 120, 120, 0.6)',
  },
};

interface AppStatusBadgeProps {
  status: AppStatus;
  size?: 'sm' | 'md';
}

export default function AppStatusBadge({ status, size = 'md' }: AppStatusBadgeProps) {
  const style = statusStyles[status];

  return (
    <span
      className={`status-badge status-badge-${size}`}
      style={{
        backgroundColor: style.backgroundColor,
        color: style.color,
        borderColor: style.borderColor,
      }}
    >
      {style.label}
    </span>
  );
}
