const { spawn } = require("node:child_process");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const envPath = join(__dirname, "..", ".env");

function loadEnv(path) {
  const env = {};

  for (const line of readFileSync(path, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    const separator = trimmed.indexOf("=");
    if (separator === -1) continue;

    env[trimmed.slice(0, separator).trim()] = trimmed.slice(separator + 1).trim();
  }

  return env;
}

const env = loadEnv(envPath);
const apiUrl = env.SUPABASE_REST_URL;
const apiKey = env.SUPABASE_KEY;

if (!apiUrl || !apiKey) {
  console.error("SUPABASE_REST_URL e SUPABASE_KEY sao obrigatorios no .env");
  process.exit(1);
}

const child = spawn(
  "npx",
  [
    "-y",
    "@supabase/mcp-server-postgrest@latest",
    "--apiUrl",
    apiUrl,
    "--apiKey",
    apiKey,
    "--schema",
    "public",
  ],
  {
    stdio: "inherit",
    shell: true,
  }
);

child.on("exit", (code) => process.exit(code ?? 0));
