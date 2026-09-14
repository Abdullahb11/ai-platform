interface PaletteSwitcherProps {
  label: string;
  index: number;
  onCycle: () => void;
}

export function PaletteSwitcher({ label, index, onCycle }: PaletteSwitcherProps) {
  return (
    <button
      className="palette-switcher"
      onClick={onCycle}
      aria-label={`Current palette: ${label}. Click to switch to next palette.`}
      title={`Palette ${index}: ${label}`}
    >
      <span className="palette-icon" aria-hidden="true"><i /><i /><i /></span>
      <span className="palette-label">{label}</span>
      <span className="palette-chevron" aria-hidden="true">↗</span>
    </button>
  );
}
