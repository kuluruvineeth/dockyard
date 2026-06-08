import type * as React from "react";
import { cn } from "~/lib/utils";

export type StatusBadgeColor = "red" | "green" | "yellow" | "gray" | "blue";

interface StatusBadgeProps {
  color?: StatusBadgeColor;
  children: React.ReactNode;
  pingState?: "animated" | "static" | "hidden";
  className?: string;
}

export function StatusBadge({
  color = "gray",
  children,
  className,
  pingState = "animated"
}: StatusBadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex border w-fit whitespace-nowrap px-2.5 py-0.5 rounded-full text-xs font-medium items-center gap-1.5",
        {
          "bg-green-600/10 border-green-600/40 text-green-700 dark:text-green-400":
            color === "green",
          "border-red-600/40 bg-red-600/10 text-red-700 dark:text-red-400":
            color === "red",
          "border-yellow-600/40 bg-yellow-600/10 text-yellow-700 dark:text-yellow-500":
            color === "yellow",
          "border-gray-500/40 bg-gray-500/10 text-gray-600 dark:text-gray-400":
            color === "gray",
          "border-blue-600/40 bg-blue-600/10 text-blue-700 dark:text-blue-300":
            color === "blue"
        },
        className
      )}
    >
      {(pingState === "animated" || pingState === "static") && (
        <div className="relative w-2 h-2">
          <span
            className={cn(
              "absolute inline-flex h-full w-full rounded-full opacity-75",
              {
                "bg-green-600": color === "green",
                "bg-red-600": color === "red",
                "bg-yellow-600": color === "yellow",
                "bg-gray-600": color === "gray",
                "bg-blue-600": color === "blue",
                "animate-ping": pingState === "animated"
              }
            )}
          />
          <span
            className={cn("relative inline-flex rounded-full h-2 w-2", {
              "bg-green-600": color === "green",
              "bg-red-600": color === "red",
              "bg-yellow-600": color === "yellow",
              "bg-gray-600": color === "gray",
              "bg-blue-600": color === "blue"
            })}
          />
        </div>
      )}
      {children}
    </div>
  );
}
