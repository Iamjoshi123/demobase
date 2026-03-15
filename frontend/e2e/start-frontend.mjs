import { resolve } from "node:path";
import { spawn } from "node:child_process";

const frontendDir = resolve(import.meta.dirname, "..");
const env = {
  ...process.env,
  BACKEND_URL: "http://127.0.0.1:8100",
};
const nextBin = process.platform === "win32" ? ".\\node_modules\\.bin\\next.cmd" : "./node_modules/.bin/next";
const server =
  process.platform === "win32"
    ? spawn(process.env.ComSpec || "cmd.exe", ["/c", `${nextBin} dev --hostname 127.0.0.1 --port 3100`], {
        cwd: frontendDir,
        env,
        stdio: "inherit",
      })
    : spawn(nextBin, ["dev", "--hostname", "127.0.0.1", "--port", "3100"], {
        cwd: frontendDir,
        env,
        stdio: "inherit",
      });

const shutdown = () => {
  if (!server.killed) {
    server.kill("SIGTERM");
  }
};

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
server.on("exit", (code) => process.exit(code ?? 0));
