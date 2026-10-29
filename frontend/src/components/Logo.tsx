interface LogoProps {
  size?: number;
  showText?: boolean;
}

export default function Logo({ size = 36, showText = true }: LogoProps) {
  return (
    <span className="logo">
      <svg width={size} height={size} viewBox="0 0 48 48" role="img" aria-label="DegreePath logo">
        <rect width="48" height="48" rx="12" fill="#57068C" />
        <path
          d="M11 35 H19 V27 H27 V19 H34"
          fill="none"
          stroke="#fff"
          strokeWidth="3.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="11" cy="35" r="3" fill="#fff" />
        <circle cx="35" cy="14" r="5" fill="#E9D5FF" />
      </svg>
      {showText && (
        <span className="logo-text">
          Degree<b>Path</b>
        </span>
      )}
    </span>
  );
}