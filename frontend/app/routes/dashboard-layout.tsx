import {
  ChevronDownIcon,
  LaptopMinimalIcon,
  LogOut,
  MoonIcon,
  SettingsIcon,
  SunIcon
} from "lucide-react";
import { Link, Outlet, redirect, useFetcher, useParams } from "react-router";
import { ThemedLogo } from "~/components/logo";
import { type Theme, useTheme } from "~/components/theme-context";
import { Button } from "~/components/ui/button";
import {
  Menubar,
  MenubarContent,
  MenubarItem,
  MenubarMenu,
  MenubarSeparator,
  MenubarTrigger
} from "~/components/ui/menubar";
import { ToggleGroup, ToggleGroupItem } from "~/components/ui/toggle-group";
import { userQueries } from "~/lib/queries";
import { queryClient } from "~/root";
import { metaTitle } from "~/utils";
import type { Route } from "./+types/dashboard-layout";

export const meta: Route.MetaFunction = () => [metaTitle("Dashboard")];

export async function clientLoader({ request }: Route.ClientLoaderArgs) {
  const [user, userExist] = await Promise.all([
    queryClient.ensureQueryData(userQueries.authedUser),
    queryClient.ensureQueryData(userQueries.checkUserExistence)
  ]);

  if (!userExist?.exists) {
    throw redirect("/onboarding");
  }
  if (!user) {
    const url = new URL(request.url);
    const redirectTo = encodeURIComponent(url.pathname + url.search);
    throw redirect(`/login?redirect_to=${redirectTo}`);
  }
  return { user };
}

export default function DashboardLayout({ loaderData }: Route.ComponentProps) {
  const { user } = loaderData;
  return (
    <div className="flex flex-col min-h-[100dvh]">
      <Header username={user.username} />
      <main className="flex-1 container mx-auto px-4 py-10 sm:py-12">
        <Outlet />
      </main>
    </div>
  );
}

function Header({ username }: { username: string }) {
  const fetcher = useFetcher();
  const { theme, setTheme } = useTheme();
  const { projectSlug, envSlug } = useParams();
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-xl">
      <div className="container mx-auto flex h-14 items-center justify-between gap-3 px-4">
        <div className="flex min-w-0 items-center gap-2.5">
          <Link to="/" className="flex flex-none items-center gap-2.5">
            <ThemedLogo className="size-7" />
            <span className="hidden font-bold tracking-tight sm:inline">
              Dockyard
            </span>
          </Link>
          {projectSlug && (
            <nav
              aria-label="Breadcrumb"
              className="flex min-w-0 items-center gap-1.5 text-sm text-grey"
            >
              <span className="text-border">/</span>
              <Link
                to={`/project/${projectSlug}/production`}
                className="truncate font-medium text-foreground transition-colors hover:text-grey"
              >
                {projectSlug}
              </Link>
              {envSlug && (
                <>
                  <span className="text-border">/</span>
                  <span className="truncate">{envSlug}</span>
                </>
              )}
            </nav>
          )}
        </div>

        <div className="flex flex-none items-center gap-1.5">
          <ToggleGroup
            type="single"
            value={theme}
            onValueChange={(value) => value && setTheme(value as Theme)}
            className="gap-1"
          >
            <ToggleGroupItem
              value="LIGHT"
              aria-label="Light theme"
              className="size-7 text-grey hover:text-foreground data-[state=on]:bg-muted data-[state=on]:text-foreground"
            >
              <SunIcon size={15} strokeWidth={1.75} />
            </ToggleGroupItem>
            <ToggleGroupItem
              value="DARK"
              aria-label="Dark theme"
              className="size-7 text-grey hover:text-foreground data-[state=on]:bg-muted data-[state=on]:text-foreground"
            >
              <MoonIcon size={15} strokeWidth={1.75} />
            </ToggleGroupItem>
            <ToggleGroupItem
              value="SYSTEM"
              aria-label="System theme"
              className="size-7 text-grey hover:text-foreground data-[state=on]:bg-muted data-[state=on]:text-foreground"
            >
              <LaptopMinimalIcon size={15} strokeWidth={1.75} />
            </ToggleGroupItem>
          </ToggleGroup>

          <Menubar className="border-none bg-transparent p-0">
            <MenubarMenu>
              <MenubarTrigger className="gap-2 cursor-pointer py-1 pl-1 pr-2 text-sm transition-colors duration-150 hover:bg-muted data-[state=open]:bg-muted">
                <span className="flex size-7 items-center justify-center bg-foreground text-[11px] font-semibold uppercase text-background">
                  {username.slice(0, 1)}
                </span>
                <span className="hidden sm:inline">{username}</span>
                <ChevronDownIcon
                  size={14}
                  strokeWidth={2}
                  className="text-grey"
                />
              </MenubarTrigger>
              <MenubarContent align="end" className="w-56">
                <MenubarItem asChild>
                  <Link to="/settings" className="flex items-center gap-2">
                    <SettingsIcon size={15} strokeWidth={1.75} />
                    Settings
                  </Link>
                </MenubarItem>
                <MenubarSeparator />
                <MenubarItem
                  className="flex items-center gap-2 text-destructive focus:text-destructive"
                  onClick={() =>
                    fetcher.submit(null, { method: "post", action: "/logout" })
                  }
                >
                  <LogOut size={15} strokeWidth={1.75} />
                  Logout
                </MenubarItem>
              </MenubarContent>
            </MenubarMenu>
          </Menubar>
        </div>
      </div>
    </header>
  );
}
