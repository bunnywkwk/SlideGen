function StatusBanner({ tone = "info", children }) {
  if (!children) {
    return null;
  }

  return <div className={`global-banner ${tone}`}>{children}</div>;
}

export default StatusBanner;
