import type { Route } from './useRoute';

interface NavigationProps {
  route: Route;
  navigate: (to: Route) => void;
}

export function Navigation({ route, navigate }: NavigationProps) {
  return (
    <nav className="platform-nav">
      <div className="nav-inner">
        <button className="brand-lockup" onClick={() => navigate('/')} aria-label="Go to AI Platform home">
          <span className="brand-mark" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span className="brand-name"><span></span></span>
        </button>
        <div className="nav-breadcrumbs">
          <button
            className={`nav-crumb${route === '/' ? ' nav-crumb-active' : ''}`}
            onClick={() => navigate('/')}
          >
            AI Platform
          </button>
          {(route === '/context-window' || route === '/context-window/current') && (
            <>
              <span className="nav-separator">/</span>
              <button
                className={`nav-crumb${route === '/context-window' ? ' nav-crumb-active' : ''}`}
                onClick={() => navigate('/context-window')}
              >
                Context Window
              </button>
            </>
          )}
          {route === '/context-window/current' && (
            <>
              <span className="nav-separator">/</span>
              <span className="nav-crumb nav-crumb-active">Current Implementation</span>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
