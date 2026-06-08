import { useQuery } from "@tanstack/react-query";
import {
  ChevronDownIcon,
  FolderIcon,
  LaptopMinimalIcon,
  LogOut,
  MoonIcon,
  PlusIcon,
  SearchIcon,
  SettingsIcon,
  SunIcon
} from "lucide-react";
import { useEffect, useState } from "react";
import {
  Link,
  Outlet,
  redirect,
  useFetcher,
  useNavigate,
  useParams
} from "react-router";
import { ThemedLogo } from "~/components/logo";
import { type Theme, useTheme } from "~/components/theme-context";
import { Button } from "~/components/ui/button";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator
} from "~/components/ui/command";
import {
  Menubar,
  MenubarContent,
  MenubarItem,
  MenubarMenu,
  MenubarSeparator,
  MenubarTrigger
} from "~/components/ui/menubar";
import { ToggleGroup, ToggleGroupItem } from "~/components/ui/toggle-group";
import { projectQueries, userQueries } from "~/lib/queries";
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

function CommandPalette() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const { data: projects } = useQuery({
    ...projectQueries.list(),
    enabled: open
  });

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setOpen((value) => !value);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  const go = (to: string) => {
    setOpen(false);
    navigate(to);
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="hidden h-8 items-center gap-6 border border-input bg-background px-2.5 text-sm text-grey transition-colors hover:border-foreground/25 hover:text-foreground md:flex"
      >
        <span className="flex items-center gap-1.5">
          <SearchIcon size={14} strokeWidth={1.75} />
          Search
        </span>
        <kbd className="font-mono text-[11px] text-grey">⌘K</kbd>
      </button>
      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput placeholder="Jump to a project or action…" />
        <CommandList>
          <CommandEmpty>No results.</CommandEmpty>
          {projects && projects.length > 0 && (
            <CommandGroup heading="Projects">
              {projects.map((project) => (
                <CommandItem
                  key={project.id}
                  value={project.slug}
                  onSelect={() => go(`/project/${project.slug}/production`)}
                >
                  <FolderIcon size={15} strokeWidth={1.75} />
                  {project.slug}
                </CommandItem>
              ))}
            </CommandGroup>
          )}
          <CommandSeparator />
          <CommandGroup heading="Actions">
            <CommandItem
              value="new project"
              onSelect={() => go("/create-project")}
            >
              <PlusIcon size={15} strokeWidth={1.75} />
              New project
            </CommandItem>
            <CommandItem value="settings" onSelect={() => go("/settings")}>
              <SettingsIcon size={15} strokeWidth={1.75} />
              Settings
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
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
          <CommandPalette />
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
