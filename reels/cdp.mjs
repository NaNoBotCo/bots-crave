// Zero-dependency Chrome driver over the DevTools protocol (Node 24 WebSocket).
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

export async function launch({ port = 9333 } = {}) {
  const profile = mkdtempSync(join(process.env.TMPDIR || tmpdir(), "mdv-chrome-"));
  const proc = spawn(CHROME, [
    "--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
    "--no-first-run", "--no-default-browser-check", "--hide-scrollbars",
    "--force-color-profile=srgb", "--lang=th-TH", "about:blank",
  ], { stdio: "ignore" });
  let ws;
  for (let i = 0; i < 100; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) { ws = page.webSocketDebuggerUrl; break; }
    } catch {}
    await new Promise((r) => setTimeout(r, 100));
  }
  if (!ws) throw new Error("chrome did not start");
  const tab = await connect(ws);
  tab.close = () => proc.kill();
  return tab;
}

async function connect(url) {
  const sock = new WebSocket(url);
  await new Promise((ok, bad) => { sock.onopen = ok; sock.onerror = bad; });
  let id = 0;
  const waiting = new Map();
  const listeners = [];
  sock.onmessage = (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id && waiting.has(msg.id)) {
      const { ok, bad } = waiting.get(msg.id);
      waiting.delete(msg.id);
      msg.error ? bad(new Error(JSON.stringify(msg.error))) : ok(msg.result);
    } else if (msg.method) listeners.forEach((f) => f(msg));
  };
  const send = (method, params = {}) => new Promise((ok, bad) => {
    const n = ++id;
    waiting.set(n, { ok, bad });
    sock.send(JSON.stringify({ id: n, method, params }));
  });
  const once = (method) => new Promise((ok) => {
    const f = (m) => { if (m.method === method) { listeners.splice(listeners.indexOf(f), 1); ok(m.params); } };
    listeners.push(f);
  });
  const tab = {
    send, once,
    async eval(expr) {
      const r = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || "eval failed");
      return r.result.value;
    },
    async size(width, height, mobile = false, scale = 1) {
      await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: scale, mobile });
      if (mobile) await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
    },
    async go(url, settle = 1500) {
      const loaded = once("Page.loadEventFired");
      await send("Page.navigate", { url });
      await Promise.race([loaded, new Promise((r) => setTimeout(r, 30000))]);
      await new Promise((r) => setTimeout(r, settle));
    },
    async shot(file, { full = false, format = "png", quality } = {}) {
      const p = { format, captureBeyondViewport: full };
      if (quality) p.quality = quality;
      if (full) {
        const m = await send("Page.getLayoutMetrics");
        const h = Math.ceil(m.cssContentSize.height);
        const w = Math.ceil(m.cssContentSize.width);
        p.clip = { x: 0, y: 0, width: w, height: h, scale: 1 };
      }
      const r = await send("Page.captureScreenshot", p);
      const buf = Buffer.from(r.data, "base64");
      if (file) (await import("node:fs")).writeFileSync(file, buf);
      return buf;
    },
  };
  await send("Page.enable");
  await send("Runtime.enable");
  return tab;
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
