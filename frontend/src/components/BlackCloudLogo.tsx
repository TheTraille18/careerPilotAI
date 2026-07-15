interface BlackCloudLogoProps {
  compact?: boolean;
}

export default function BlackCloudLogo({ compact = false }: BlackCloudLogoProps) {
  const markSize = compact ? 38 : 46;

  return (
    <span className={`bc-logo${compact ? ' bc-logo-compact' : ''}`}>
      <svg
        className="bc-logo-mark"
        width={markSize}
        height={markSize}
        viewBox="0 0 48 48"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden
      >
        <defs>
          <linearGradient id="bc-cloud-fill" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#1a2233" />
            <stop offset="100%" stopColor="#0b1018" />
          </linearGradient>
          <linearGradient id="bc-cloud-edge" x1="0%" y1="50%" x2="100%" y2="50%">
            <stop offset="0%" stopColor="#5eb3ff" stopOpacity="0.2" />
            <stop offset="50%" stopColor="#9fd4ff" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#5eb3ff" stopOpacity="0.2" />
          </linearGradient>
        </defs>
        <path
          d="M14 30c-4.4 0-8-3.1-8-7 0-3.4 2.4-6.2 5.7-6.9C13.2 10.8 18.2 8 24 8c5.2 0 9.7 2.3 12.4 6 3.5.5 6.1 3.4 6.1 6.8 0 3.8-3.1 6.9-7 7.1H14z"
          fill="url(#bc-cloud-fill)"
          stroke="url(#bc-cloud-edge)"
          strokeWidth="1.5"
        />
        <path
          d="M18 34h12"
          stroke="#7ec8ff"
          strokeWidth="2"
          strokeLinecap="round"
          opacity="0.85"
        />
        <circle cx="24" cy="22" r="2.5" fill="#b8dcff" opacity="0.9" />
      </svg>
      <span className="bc-logo-wordmark">
        <span className="bc-logo-line">
          <span className="bc-logo-accent">A</span> Black Cloud App
        </span>
      </span>
    </span>
  );
}
