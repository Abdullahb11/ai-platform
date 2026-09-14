import './App.css';
import './pages.css';
import './themes/theme.css';
import { useRoute } from './useRoute';
import { useTheme } from './themes/useTheme';
import { Navigation } from './Navigation';
import { PaletteSwitcher } from './themes/PaletteSwitcher';
import { HomePage } from './HomePage';
import { ContextWindowPage } from './ContextWindowPage';
import { ContextWindowChat } from './ContextWindowChat';

function App() {
  const { route, navigate } = useRoute();
  const { label, index, cycle } = useTheme();

  return (
    <>
      <PaletteSwitcher label={label} index={index} onCycle={cycle} />
      {route !== '/context-window/current' && (
        <Navigation route={route} navigate={navigate} />
      )}
      {route === '/' && <HomePage navigate={navigate} />}
      {route === '/context-window' && <ContextWindowPage navigate={navigate} />}
      {route === '/context-window/current' && <ContextWindowChat />}
    </>
  );
}

export default App;
