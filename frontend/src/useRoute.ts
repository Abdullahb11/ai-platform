import { useState, useEffect, useCallback } from 'react';

export type Route = '/' | '/context-window' | '/context-window/current';

function getRoute(): Route {
  const hash = window.location.hash.replace(/^#/, '') || '/';
  if (hash === '/context-window/current') return '/context-window/current';
  if (hash === '/context-window') return '/context-window';
  return '/';
}

export function useRoute() {
  const [route, setRoute] = useState<Route>(getRoute);

  useEffect(() => {
    const onHashChange = () => setRoute(getRoute());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const navigate = useCallback((to: Route) => {
    window.location.hash = '#' + to;
  }, []);

  return { route, navigate };
}
