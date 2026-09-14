interface ConceptCardProps {
  title: string;
  description: string;
  status: 'available' | 'coming-soon';
  onAction?: () => void;
  actionLabel?: string;
  icon?: string;
}

export function ConceptCard({ title, description, status, onAction, actionLabel, icon }: ConceptCardProps) {
  return (
    <div className={`concept-card ${status}`}>
      <div className="concept-card-topline">
        <span className="concept-card-index">{status === 'available' ? '01' : '—'}</span>
        <span className={`concept-card-badge ${status}`}>
          {status === 'available' ? 'Available' : 'Coming soon'}
        </span>
      </div>
      <div className="concept-card-header">
        {icon && <span className="concept-card-icon" aria-hidden="true">{icon}</span>}
        <h3 className="concept-card-title">{title}</h3>
      </div>
      <p className="concept-card-desc">{description}</p>
      {status === 'available' && onAction && (
        <button className="concept-card-action" onClick={onAction}>
          {actionLabel || 'Explore'} <span aria-hidden="true">↗</span>
        </button>
      )}
      {status === 'coming-soon' && <span className="concept-card-rule" />}
    </div>
  );
}
