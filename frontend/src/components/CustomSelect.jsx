import { useEffect, useMemo, useRef, useState } from "react";

function CustomSelect({
  label,
  value,
  options,
  onChange,
  placeholder = "Select...",
  searchable = false,
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef(null);

  const selectedOption = useMemo(
    () => options.find((option) => option.value === value) ?? null,
    [options, value],
  );

  const filteredOptions = useMemo(() => {
    if (!searchable || !query.trim()) {
      return options;
    }

    const normalized = query.trim().toLowerCase();
    return options.filter((option) => option.label.toLowerCase().includes(normalized));
  }, [options, query, searchable]);

  useEffect(() => {
    function handleOutsideClick(event) {
      if (!rootRef.current?.contains(event.target)) {
        setOpen(false);
        setQuery("");
      }
    }

    function handleEscape(event) {
      if (event.key === "Escape") {
        setOpen(false);
        setQuery("");
      }
    }

    document.addEventListener("mousedown", handleOutsideClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  function handleSelect(nextValue) {
    onChange(nextValue);
    setOpen(false);
    setQuery("");
  }

  return (
    <label className="field custom-select-field" ref={rootRef}>
      {label ? <span>{label}</span> : null}
      <div className={open ? "custom-select open" : "custom-select"}>
        <button
          type="button"
          className="custom-select-trigger"
          onClick={() => setOpen((current) => !current)}
          aria-expanded={open}
        >
          <span className="custom-select-value">
            {selectedOption?.color ? <span className="color-chip" style={{ backgroundColor: selectedOption.color }} /> : null}
            <span>{selectedOption?.label ?? placeholder}</span>
          </span>
          <span className="custom-select-arrow" />
        </button>

        {open ? (
          <div className="custom-select-menu">
            {searchable ? (
              <input
                className="custom-select-search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={`Search ${label?.toLowerCase() || "options"}...`}
                autoFocus
              />
            ) : null}

            <div className="custom-select-options">
              {filteredOptions.length > 0 ? (
                filteredOptions.map((option) => (
                  <button
                    type="button"
                    key={option.value}
                    className={option.value === value ? "custom-option active" : "custom-option"}
                    onClick={() => handleSelect(option.value)}
                  >
                    {option.color ? <span className="color-chip" style={{ backgroundColor: option.color }} /> : null}
                    <span>{option.label}</span>
                  </button>
                ))
              ) : (
                <div className="custom-option-empty">No matches found.</div>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </label>
  );
}

export default CustomSelect;
