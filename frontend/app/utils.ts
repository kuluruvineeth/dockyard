import { apiClient } from "~/api/client";

export async function getCsrfTokenHeader() {
  await apiClient.GET("/api/csrf");
  return { "X-CSRFToken": getCookie("csrftoken") };
}

export function excerpt(text: string, maxLength: number): string {
  if (text.length <= maxLength) {
    return text;
  }
  return text.substring(0, maxLength).trimEnd() + "...";
}

export function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(";").shift() ?? null;
  }
  return null;
}

export function setCookie(
  name: string,
  value: string,
  days?: number,
  options: {
    path?: string;
    secure?: boolean;
    sameSite?: "Strict" | "Lax" | "None";
  } = {}
): void {
  let cookie = `${encodeURIComponent(name)}=${encodeURIComponent(value)}`;

  if (days) {
    const date = new Date();
    date.setTime(date.getTime() + days * 864e5);
    cookie += `; expires=${date.toUTCString()}`;
  }

  cookie += `; path=${options.path ?? "/"}`;

  if (options.secure) cookie += "; Secure";
  if (options.sameSite) cookie += `; SameSite=${options.sameSite}`;

  document.cookie = cookie;
}

export function deleteCookie(name: string): void {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
}

export function formattedDate(dateInput: string | Date): string {
  const date = new Date(dateInput);
  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    day: "numeric",
    year: "numeric"
  }).format(date);
}

export function formattedTime(dateInput: string | Date): string {
  const date = new Date(dateInput);
  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    hour: "numeric",
    minute: "numeric",
    second: "numeric",
    day: "numeric",
    year: "numeric"
  }).format(date);
}

export function capitalizeText(text: string): string {
  return text.charAt(0).toUpperCase() + text.substring(1).toLowerCase();
}

export function formatURL({
  domain,
  base_path = "/"
}: { domain: string; base_path?: string }) {
  const currentUrl = new URL(window.location.href);
  return `${currentUrl.protocol}//${domain}${base_path}`;
}

export function pluralize(word: string, item_count: number) {
  return word + (item_count > 1 ? "s" : "");
}

export function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function isArrayOfNumbers(arr: any): arr is number[] {
  if (!Array.isArray(arr)) return false;
  return arr.every((item) => typeof item === "number");
}

export function metaTitle(title: string) {
  return { title: `${title} | Dockyard` } as const;
}

export function durationToMs(
  value: number,
  unit: "seconds" | "minutes" | "hours" | "days" | "weeks"
): number {
  const multipliers = {
    seconds: 1000,
    minutes: 60 * 1000,
    hours: 60 * 60 * 1000,
    days: 24 * 60 * 60 * 1000,
    weeks: 7 * 24 * 60 * 60 * 1000
  };
  return value * multipliers[unit];
}
