import type * as React from "react";
import { cn } from "~/lib/utils";

export type CodeProps = Omit<React.HTMLAttributes<HTMLDivElement>, "ref">;

export function Code({ className, ...props }: CodeProps) {
  return (
    <code
      className={cn(
        "font-mono border border-border bg-muted px-1 py-0.5 text-foreground",
        className
      )}
      {...props}
    />
  );
}
