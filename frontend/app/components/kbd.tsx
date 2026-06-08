import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cn } from "~/lib/utils";

export const kbdVariants = cva(
  "select-none px-1.5 py-px font-mono text-[0.7rem] font-normal shadow-xs disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "border border-border bg-muted text-foreground",
        outline: "border border-border bg-background text-foreground"
      }
    },
    defaultVariants: {
      variant: "default"
    }
  }
);

export interface KbdProps
  extends React.ComponentPropsWithoutRef<"kbd">,
    VariantProps<typeof kbdVariants> {
  abbrTitle?: string;
  ref?: React.RefObject<HTMLElement>;
}

const Kbd = ({
  ref,
  abbrTitle,
  children,
  className,
  variant,
  ...props
}: KbdProps) => {
  return (
    <kbd
      className={cn(kbdVariants({ variant, className }))}
      ref={ref}
      {...props}
    >
      {abbrTitle ? (
        <abbr title={abbrTitle} className="no-underline">
          {children}
        </abbr>
      ) : (
        children
      )}
    </kbd>
  );
};

export { Kbd };
