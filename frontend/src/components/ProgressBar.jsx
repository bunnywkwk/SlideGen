import { useEffect, useMemo, useState } from "react";

function ProgressBar({ active, label, accent = "teal", progressValue = null }) {
  const [progress, setProgress] = useState(0);
  const [visible, setVisible] = useState(false);

  const accentClass = useMemo(() => {
    return accent === "orange" ? "progress-fill orange" : "progress-fill teal";
  }, [accent]);

  useEffect(() => {
    let intervalId;
    let timeoutId;

    if (active && typeof progressValue === "number") {
      setVisible(true);
      setProgress(Math.max(4, Math.min(100, progressValue)));
    } else if (active) {
      setVisible(true);
      setProgress((current) => (current > 12 ? current : 12));

      intervalId = window.setInterval(() => {
        setProgress((current) => {
          if (current < 55) {
            return Math.min(current + 8, 55);
          }
          if (current < 80) {
            return Math.min(current + 4, 80);
          }
          if (current < 93) {
            return Math.min(current + 1.2, 93);
          }
          if (current < 97) {
            return Math.min(current + 0.4, 97);
          }
          return current;
        });
      }, 180);
    } else if (visible) {
      setProgress(100);
      timeoutId = window.setTimeout(() => {
        setVisible(false);
        setProgress(0);
      }, 420);
    }

    return () => {
      if (intervalId) {
        window.clearInterval(intervalId);
      }
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [active, progressValue, visible]);

  if (!visible) {
    return null;
  }

  return (
    <div className="progress-overlay" role="dialog" aria-modal="true" aria-live="polite">
      <div className="progress-panel">
        <div className="progress-copy">
          <span>{label || "Loading..."}</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="progress-track">
          <div className={accentClass} style={{ width: `${progress}%` }} />
        </div>
        <p className="progress-helper">Please wait while we finish the request.</p>
      </div>
    </div>
  );
}

export default ProgressBar;
