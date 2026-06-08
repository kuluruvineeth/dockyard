import {
  QueryClient,
  QueryClientProvider,
  keepPreviousData
} from "@tanstack/react-query";
import * as React from "react";
import {
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
  isRouteErrorResponse,
  useRouteError
} from "react-router";
import { ThemeProvider, getThemePreference } from "~/components/theme-context";
import { THEME_STORAGE_KEY } from "~/lib/constants";
import type { Route } from "./+types/root";
import stylesheet from "./app.css?url";

export function links() {
  return [
    { rel: "stylesheet", href: stylesheet }
  ] satisfies ReturnType<Route.LinksFunction>;
}

export function meta() {
  return [{ title: "Dockyard" }] satisfies ReturnType<Route.MetaFunction>;
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      placeholderData: keepPreviousData,
      retry(failureCount, error) {
        return !(error instanceof Response) && failureCount < 3;
      }
    }
  }
});

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <Meta />
        <Links />
      </head>
      <body className="overflow-x-clip">
        {children}

        <ScrollRestoration />
        <Scripts />

        <script
          defer
          dangerouslySetInnerHTML={{
            __html: `
              (function () {
                function setTheme(newTheme) {
                  if (newTheme === 'DARK') {
                    document.documentElement.dataset.theme = 'dark';
                  } else if (newTheme === 'LIGHT') {
                    document.documentElement.dataset.theme = 'light';
                  }
                }
                var initialTheme = localStorage.getItem('${THEME_STORAGE_KEY}');
                var darkQuery = window.matchMedia('(prefers-color-scheme: dark)');
                if (!initialTheme) {
                  initialTheme = darkQuery.matches ? 'DARK' : 'LIGHT';
                }
                setTheme(initialTheme);
                darkQuery.addEventListener('change', function (e) {
                  const preferredTheme = localStorage.getItem('${THEME_STORAGE_KEY}');
                  if (!preferredTheme) {
                    setTheme(e.matches ? 'DARK' : 'LIGHT');
                  }
                });
              })();
            `
          }}
        />
      </body>
    </html>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <Outlet />
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export function HydrateFallback() {
  return (
    <div className="flex h-screen items-center justify-center">Loading…</div>
  );
}

export function ErrorBoundary() {
  let message = "Oops!";
  let details = "An unexpected error occurred.";
  let stack: string | undefined;
  const error = useRouteError();

  if (isRouteErrorResponse(error)) {
    message = error.status === 404 ? "Oops!" : "Error";
    details =
      error.status === 404
        ? (error.data ?? "Looks like you're lost 😛")
        : error.statusText || details;
  } else if (error && error instanceof Error) {
    details = error.message;
    stack = error.stack;
  }

  React.useEffect(() => {
    const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const theme = getThemePreference();
    if (theme === "DARK") {
      document.documentElement.dataset.theme = "dark";
    } else if (theme === "LIGHT") {
      document.documentElement.dataset.theme = "light";
    } else {
      document.documentElement.dataset.theme = darkQuery.matches
        ? "dark"
        : "light";
    }
  }, []);

  return (
    <div className="flex flex-col gap-5 h-screen items-center justify-center px-5">
      <div className="flex-col flex gap-3 items-center">
        <h1 className="text-3xl font-bold">{message}</h1>
        <p className="text-lg">{details}</p>
      </div>
      {stack ? (
        <pre className="w-full p-4 overflow-x-auto bg-red-400/20">
          <code>{stack}</code>
        </pre>
      ) : null}
    </div>
  );
}
