import { spawn } from "child_process";
import { existsSync } from "fs";
import path from "path";

type BridgeResponse<T> = {
  success: boolean;
  error?: string;
} & T;

const pythonCommand = process.platform === "win32" ? "py" : "python3";

export async function forwardToBackend<T>(
  endpoint: string,
  payload: unknown,
): Promise<BridgeResponse<T>> {
  const backendUrl = process.env.BACKEND_API_URL;

  if (backendUrl) {
    return callHttpBackend<T>(backendUrl, endpoint, payload);
  }

  const scriptName = endpoint === "/api/dashboard" ? "api_dashboard.py" : "api_order.py";
  return runPythonBridge<T>(scriptName, payload);
}

async function callHttpBackend<T>(
  backendUrl: string,
  endpoint: string,
  payload: unknown,
): Promise<BridgeResponse<T>> {
  try {
    const response = await fetch(`${backendUrl.replace(/\/$/, "")}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (!response.ok) {
      return {
        success: false,
        error: data.detail || data.error || "Backend request failed.",
      } as BridgeResponse<T>;
    }

    return data as BridgeResponse<T>;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Backend request failed.";
    return { success: false, error: message } as BridgeResponse<T>;
  }
}

function runPythonBridge<T>(
  scriptName: string,
  payload: unknown,
): Promise<BridgeResponse<T>> {
  return new Promise((resolve) => {
    const botRoot = resolveBackendDirectory();
    const scriptPath = path.join(botRoot, scriptName);
    const child = spawn(pythonCommand, [scriptPath], {
      cwd: botRoot,
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });

    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });

    child.on("error", (error) => {
      resolve({
        success: false,
        error: `Unable to start Python process: ${error.message}`,
      } as BridgeResponse<T>);
    });

    child.on("close", () => {
      const lastLine = stdout.trim().split(/\r?\n/).filter(Boolean).at(-1);

      if (!lastLine) {
        resolve({
          success: false,
          error: stderr.trim() || "Python process returned no response.",
        } as BridgeResponse<T>);
        return;
      }

      try {
        resolve(JSON.parse(lastLine) as BridgeResponse<T>);
      } catch {
        resolve({
          success: false,
          error: "Python process returned an invalid response.",
        } as BridgeResponse<T>);
      }
    });

    child.stdin.write(JSON.stringify(payload));
    child.stdin.end();
  });
}

function resolveBackendDirectory() {
  if (process.env.TRADING_BOT_BACKEND_DIR) {
    return process.env.TRADING_BOT_BACKEND_DIR;
  }

  const siblingBackend = path.resolve(process.cwd(), "..", "trading_bot");
  if (existsSync(path.join(siblingBackend, "api_order.py"))) {
    return siblingBackend;
  }

  return path.resolve(process.cwd(), "..");
}

