import { existsSync, mkdirSync, unlinkSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const local = join(root, ".tools", process.platform === "win32" ? "wasm-pack.exe" : "wasm-pack");
const command = existsSync(local) ? local : "wasm-pack";
const localCargoBin = join(root, ".tools", "cargo", "bin");
const localTemp = join(root, ".tools", "tmp");
mkdirSync(localTemp, { recursive: true });
const env = existsSync(localCargoBin)
  ? { ...process.env, PATH: `${localCargoBin}${process.platform === "win32" ? ";" : ":"}${process.env.PATH ?? ""}`, CARGO_HOME: join(root, ".tools", "cargo"), RUSTUP_HOME: join(root, ".tools", "rustup"), TEMP: localTemp, TMP: localTemp }
  : process.env;
// Keep generated glue in the source graph so Vite transforms the module and
// emits its referenced WASM asset in development and production builds.
const output = join(root, "frontend", "src", "features", "rust-viewer", "wasm", "generated");
mkdirSync(output, { recursive: true });
const result = spawnSync(command, ["build", join(root, "rust-viewer"), "--target", "web", "--release", "--out-dir", output, "--out-name", "brainon_rust_viewer"], { stdio: "inherit", env });
if (result.error) throw result.error;
const generatedIgnore = join(output, ".gitignore");
if (existsSync(generatedIgnore)) unlinkSync(generatedIgnore);
process.exit(result.status ?? 1);
