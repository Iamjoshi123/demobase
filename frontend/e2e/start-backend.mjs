import { existsSync, rmSync } from "node:fs";
import { resolve } from "node:path";
import { spawn, spawnSync } from "node:child_process";

const repoRoot = resolve(import.meta.dirname, "..", "..");
const backendDir = resolve(repoRoot, "backend");
const dbPath = resolve(backendDir, "e2e.db");
const python = process.env.PYTHON || "C:\\Python313\\python.exe";

if (existsSync(dbPath)) {
  rmSync(dbPath, { force: true });
}

const env = {
  ...process.env,
  APP_ENV: "test",
  DATABASE_URL: "sqlite:///./e2e.db",
  FRONTEND_URL: "http://127.0.0.1:3100",
  BACKEND_URL: "http://127.0.0.1:8100",
  ENCRYPTION_KEY: "rHtpqtHXdq8jToWMunn1ep1jI2iw39QnpPRy01JCL5g=",
};

const seed = spawnSync(python, ["-m", "app.seed"], {
  cwd: backendDir,
  env,
  stdio: "inherit",
});

if (seed.status !== 0) {
  process.exit(seed.status ?? 1);
}

const server = spawn(
  python,
  ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8100"],
  {
    cwd: backendDir,
    env,
    stdio: "inherit",
  },
);

const shutdown = () => {
  if (!server.killed) {
    server.kill("SIGTERM");
  }
};

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
server.on("exit", (code) => process.exit(code ?? 0));
