import type { Route } from './useRoute';
import { ConceptCard } from './ConceptCard';

interface ContextWindowPageProps {
  navigate: (to: Route) => void;
}

export function ContextWindowPage({ navigate }: ContextWindowPageProps) {
  return (
    <div className="page-container">
      <div className="page-hero">
        <div className="hero-eyebrow"><span className="eyebrow-line" /> MODULE 01 / CONTEXT <span className="eyebrow-line" /></div>
        <h1 className="page-title">Make every token<br /><em>count.</em></h1>
        <p className="page-subtitle">Managing conversation context within token limits.</p>
        <p className="page-description">
          When conversations grow beyond a model’s context budget, the system needs a point
          of view. Compare strategies for deciding what to keep, what to compress, and what
          to retrieve.
        </p>
        <div className="hero-meta">
          <span><strong>03</strong> approaches mapped</span>
          <span className="meta-divider" />
          <span><strong>01</strong> ready to run</span>
        </div>
      </div>

      <section className="concepts-section">
        <div className="section-heading-row">
          <div>
            <span className="section-kicker">Choose a direction</span>
            <h2 className="section-heading">Context strategies</h2>
          </div>
          <span className="section-count">01 — 03</span>
        </div>
        <div className="concepts-grid">
          <ConceptCard
            icon="◫"
            title="Current Implementation"
            description="A sliding-window approach that keeps complete conversation turns within a configurable application context limit. Includes real-time context inspection, snapshot history, and complete-turn preservation."
            status="available"
            onAction={() => navigate('/context-window/current')}
            actionLabel="Open Implementation"
          />
          <ConceptCard
            icon="⊞"
            title="RAG-based Context"
            description="Retrieval-based context selection — instead of keeping recent messages, retrieve the most relevant past messages using semantic search."
            status="coming-soon"
          />
          <ConceptCard
            icon="≡"
            title="Summarization-based Context"
            description="Compressing older conversation history into progressive summaries, preserving key information while freeing token budget for new messages."
            status="coming-soon"
          />
        </div>
      </section>
    </div>
  );
}
