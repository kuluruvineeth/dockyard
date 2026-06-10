import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";
import { TerminalIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "~/lib/utils";

type ConnStatus = "connecting" | "open" | "closed";

const STATUS: Record<ConnStatus, { dot: string; label: string }> = {
  connecting: { dot: "bg-white/40", label: "connecting" },
  open: { dot: "bg-emerald-500", label: "connected" },
  closed: { dot: "bg-red-400", label: "disconnected" }
};

function fmtUptime(ms: number): string {
  const total = Math.floor(ms / 1000);
  const hh = Math.floor(total / 3600);
  const mm = Math.floor((total % 3600) / 60);
  const ss = total % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return hh > 0 ? `${hh}:${pad(mm)}:${pad(ss)}` : `${pad(mm)}:${pad(ss)}`;
}

export function DeploymentTerminal({
  projectSlug,
  envSlug,
  serviceSlug,
  hash
}: {
  projectSlug: string;
  envSlug: string;
  serviceSlug: string;
  hash: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<ConnStatus>("connecting");
  const [uptime, setUptime] = useState(0);

  useEffect(() => {
    setStatus("connecting");
    const el = ref.current;
    if (!el) return;

    const term = new Terminal({
      fontFamily: '"Geist-Mono", ui-monospace, monospace',
      fontSize: 13,
      cursorBlink: true,
      theme: { background: "#0a0a0a", foreground: "#e4e4e7" }
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(el);
    fit.fit();

    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(
      `${proto}://${window.location.host}/api/projects/${projectSlug}/${envSlug}/service-details/${serviceSlug}/deployments/${hash}/terminal/`
    );
    ws.binaryType = "arraybuffer";

    const sendResize = () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows })
        );
      }
    };

    ws.onopen = () => {
      fit.fit();
      sendResize();
      setStatus("open");
    };
    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        term.write(event.data);
      } else {
        term.write(new Uint8Array(event.data as ArrayBuffer));
      }
    };
    ws.onclose = () => {
      term.write("\r\n\x1b[90m[connection closed]\x1b[0m\r\n");
      setStatus("closed");
    };

    const onData = term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "input", data }));
      }
    });
    const onResize = term.onResize(() => sendResize());
    const onWindowResize = () => fit.fit();
    window.addEventListener("resize", onWindowResize);

    return () => {
      window.removeEventListener("resize", onWindowResize);
      onData.dispose();
      onResize.dispose();
      ws.close();
      term.dispose();
    };
  }, [projectSlug, envSlug, serviceSlug, hash]);

  // Presentational uptime, derived from connection status only.
  useEffect(() => {
    if (status !== "open") {
      setUptime(0);
      return;
    }
    const start = Date.now();
    const id = window.setInterval(() => setUptime(Date.now() - start), 1000);
    return () => window.clearInterval(id);
  }, [status]);

  return (
    <div className="overflow-hidden border border-white/10 bg-[#0a0a0a]">
      <div className="flex flex-col sm:flex-row">
        <aside className="flex flex-none flex-col divide-y divide-white/10 border-b border-white/10 sm:w-52 sm:border-b-0 sm:border-r">
          <div className="flex items-center gap-2 px-4 py-3">
            <TerminalIcon
              size={13}
              strokeWidth={1.75}
              className="text-white/40"
            />
            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-white/40">
              Terminal
            </span>
          </div>
          <RailCell label="Session" value={serviceSlug} />
          <RailCell label="Deployment" value={hash} />
          <RailCell
            label="Uptime"
            value={status === "open" ? fmtUptime(uptime) : "—"}
          />
          <div className="flex flex-col gap-1 px-4 py-3">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/30">
              Connection
            </span>
            <span className="inline-flex items-center gap-1.5 font-mono text-xs uppercase tracking-[0.12em] text-white/60">
              <span
                className={cn("size-1.5 rounded-full", STATUS[status].dot)}
              />
              {STATUS[status].label}
            </span>
          </div>
        </aside>
        <div
          ref={ref}
          className="h-72 min-w-0 flex-1 overflow-hidden p-2 sm:h-80"
        />
      </div>
    </div>
  );
}

function RailCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 px-4 py-3">
      <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/30">
        {label}
      </span>
      <span className="truncate font-mono text-xs tabular-nums text-white/70">
        {value}
      </span>
    </div>
  );
}
