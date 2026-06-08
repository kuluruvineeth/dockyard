import * as React from "react";
import { z } from "zod";
import { THEME_STORAGE_KEY } from "~/lib/constants";

const themeSchema = z.enum(["LIGHT", "DARK", "SYSTEM"]);
export type Theme = z.infer<typeof themeSchema>;

export type ThemeProviderProps = {
  children: React.ReactNode;
  defaultTheme?: Theme;
};

type ThemeContextValue = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
};

const ThemeContext = React.createContext<ThemeContextValue | undefined>(
  undefined
);

export function getThemePreference(): Theme {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  const parseResult = themeSchema.safeParse(stored);
  return parseResult.success ? parseResult.data : "SYSTEM";
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const [theme, setThemeState] = React.useState<Theme>(getThemePreference);

  function setTheme(newTheme: Theme) {
    const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");

    if (newTheme === "DARK") {
      document.documentElement.dataset.theme = "dark";
      localStorage.setItem(THEME_STORAGE_KEY, "DARK");
    } else if (newTheme === "LIGHT") {
      document.documentElement.dataset.theme = "light";
      localStorage.setItem(THEME_STORAGE_KEY, "LIGHT");
    } else {
      document.documentElement.dataset.theme = darkQuery.matches
        ? "dark"
        : "light";
      localStorage.removeItem(THEME_STORAGE_KEY);
    }

    setThemeState(newTheme);
  }

  React.useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === THEME_STORAGE_KEY) {
        setThemeState(getThemePreference());
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return <ThemeContext value={{ theme, setTheme }}>{children}</ThemeContext>;
}

export function useTheme() {
  const context = React.use(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}
