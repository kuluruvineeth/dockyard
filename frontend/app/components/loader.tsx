import { cn } from "~/lib/utils";

type LoaderProps = { className?: string };
export function Loader({ className }: LoaderProps) {
  return (
    <div className={cn("flex h-screen items-center justify-center", className)}>
      <svg
        className="loader-svg w-52"
        data-name="Layer 1"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 512 512"
      >
        <path
          pathLength={1400}
          d="M96 32h150c123.7 0 224 100.3 224 224S369.7 480 246 480H96a32 32 0 0 1-32-32V64a32 32 0 0 1 32-32Z"
        />
      </svg>
    </div>
  );
}
