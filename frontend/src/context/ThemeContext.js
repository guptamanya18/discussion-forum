/** This file controls the colors and style of the whole website. */
import { createContext, useContext, useState, useMemo } from 'react';

// mui applies theme to entire app
import { ThemeProvider as MuiThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import getTheme from '../theme';

// context shre themes across all app
const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const [mode, setMode] = useState(() => localStorage.getItem('themeMode') || 'dark');

  const toggleTheme = () => {
    setMode(prev => {

      //switching from dark to light or vice-versa
      const next = prev === 'dark' ? 'light' : 'dark';
      localStorage.setItem('themeMode', next);
      return next;
    });
  };


  // memo avoids recalculating themes at every render
  const theme = useMemo(() => getTheme(mode), [mode]);

  return (
    <ThemeContext.Provider value={{ mode, toggleTheme }}>
      <MuiThemeProvider theme={theme}>

        {/* normalize css across different browsers */}
        <CssBaseline />
        {children}
      </MuiThemeProvider>
    </ThemeContext.Provider>
  );
}

export function useThemeMode() {
  return useContext(ThemeContext);
}
