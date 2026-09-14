import type { Route } from './useRoute';
import { ConceptCard } from './ConceptCard';

interface HomePageProps {
  navigate: (to: Route) => void;
}

export function HomePage({ navigate }: HomePageProps) {
  return (
    <div className="page-container">
      <div className="page-hero">
        <div className="hero-eyebrow"><span className="eyebrow-line" /> AI SYSTEMS / 01 <span className="eyebrow-line" /></div>
        <h1 className="page-title">Build intelligence<br /><em>with intention.</em></h1>
        <p className="page-subtitle">A hands-on lab for the systems behind exceptional AI products.</p>
        <p className="page-description">
          Explore the mechanics that make AI applications feel thoughtful, reliable, and
          useful. Every concept is implemented end-to-end so you can see the engineering,
          not just the theory.
        </p>
        <div className="hero-meta">
          <span><strong>08</strong> learning modules</span>
          <span className="meta-divider" />
          <span><strong>01</strong> live implementation</span>
          <span className="meta-divider" />
          <span><strong>∞</strong> room to experiment</span>
        </div>
      </div>

      <section className="concepts-section">
        <div className="section-heading-row">
          <div>
            <span className="section-kicker">The curriculum</span>
            <h2 className="section-heading">Explore the building blocks</h2>
          </div>
          <span className="section-count">01 — 08</span>
        </div>
        <div className="concepts-grid">
          <ConceptCard
            icon="◫"
            title="Context Window"
            description="Explore how AI applications manage conversation context within token limits. Understand sliding-window truncation, complete-turn preservation, and context-budget trade-offs."
            status="available"
            onAction={() => navigate('/context-window')}
          />
          <ConceptCard
            icon="⊞"
            title="RAG"
            description="Retrieval-Augmented Generation — grounding model responses in external knowledge by retrieving relevant documents at query time."
            status="coming-soon"
          />
          <ConceptCard
            icon="≡"
            title="Summarization"
            description="Compressing conversation history or documents into concise summaries to preserve key information within limited context budgets."
            status="coming-soon"
          />
          <ConceptCard
            icon="⟲"
            title="Memory"
            description="Giving AI applications long-term memory beyond a single conversation — persisting user preferences, facts, and interaction patterns."
            status="coming-soon"
          />
          <ConceptCard
            icon="⚙"
            title="Agents"
            description="Autonomous AI systems that can plan, reason, and execute multi-step tasks using tools and external APIs."
            status="coming-soon"
          />
          <ConceptCard
            icon="⛏"
            title="Tool Calling"
            description="Enabling models to invoke structured functions — API calls, database queries, calculations — and incorporate results into responses."
            status="coming-soon"
          />
          <ConceptCard
            icon="✎"
            title="Prompt Engineering"
            description="Systematic approaches to crafting prompts that reliably produce high-quality outputs — templates, few-shot examples, and chain-of-thought."
            status="coming-soon"
          />
          <ConceptCard
            icon="◉"
            title="Evaluation"
            description="Measuring AI application quality — automated metrics, human evaluation frameworks, and regression testing for model outputs."
            status="coming-soon"
          />
        </div>
      </section>
    </div>
  );
}
