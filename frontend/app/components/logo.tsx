import type * as React from "react";
import { useTheme } from "~/components/theme-context";
import { cn } from "~/lib/utils";
import logoSymbolBlack from "/logo/Dockyard-SYMBOL-BLACK.svg";
import logoSymbolWhite from "/logo/Dockyard-SYMBOL-WHITE.svg";

export function ThemedLogo({ className }: { className?: string }) {
  const theme = useTheme().theme;
  return (
    <picture
      className={cn(
        "flex justify-center items-center size-[100px] flex-none",
        className
      )}
    >
      {theme === "SYSTEM" && (
        <>
          <source
            media="(prefers-color-scheme: dark)"
            srcSet={logoSymbolWhite}
          />
          <source
            media="(prefers-color-scheme: light)"
            srcSet={logoSymbolBlack}
          />
        </>
      )}
      <img
        src={theme === "DARK" ? logoSymbolWhite : logoSymbolBlack}
        alt="Dockyard logo"
      />
    </picture>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <>
      <img
        src={logoSymbolWhite}
        alt="Dockyard logo"
        className={cn(
          "flex justify-center items-center size-[100px] flex-none",
          "!hidden dark:!block",
          className
        )}
      />
      <img
        src={logoSymbolBlack}
        alt="Dockyard logo"
        className={cn(
          "flex justify-center items-center size-[100px] flex-none",
          "block dark:hidden",
          className
        )}
      />
    </>
  );
}

export function DockyardLogo(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      data-name="Layer 1"
      viewBox="0 0 512 512"
      {...props}
    >
      <path
        fillRule="evenodd"
        d="M96 32h150c123.7 0 224 100.3 224 224S369.7 480 246 480H96a32 32 0 0 1-32-32V64a32 32 0 0 1 32-32Zm64 80v288h86c79.5 0 144-64.5 144-144s-64.5-144-144-144h-86Z"
        style={{ fill: "currentColor", strokeWidth: 0 }}
      />
      <path
        d="M218 178h104a14 14 0 0 1 0 28H218a14 14 0 0 1 0-28Zm0 64h104a14 14 0 0 1 0 28H218a14 14 0 0 1 0-28Zm0 64h104a14 14 0 0 1 0 28H218a14 14 0 0 1 0-28Z"
        style={{ fill: "currentColor", strokeWidth: 0 }}
      />
    </svg>
  );
}
