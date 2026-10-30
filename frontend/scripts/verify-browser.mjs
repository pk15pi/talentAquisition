import { mkdir } from "node:fs/promises";
import { chromium } from "playwright-core";

const frontend = process.env.FRONTEND_URL || "http://localhost:5173";
const api = process.env.API_URL || "http://127.0.0.1:8000/api/v1";
const outDir = process.env.SCREENSHOT_DIR || "/opt/cursor/artifacts/screenshots";
const username = process.env.VERIFY_USER || "hrbrowser";
const password = process.env.VERIFY_PASSWORD || "longpassword1";

const browser = await chromium.launch({
  executablePath: process.env.CHROME_PATH || "/usr/local/bin/google-chrome",
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
await mkdir(outDir, { recursive: true });

async function shot(name) {
  const path = `${outDir}/${name}.png`;
  await page.screenshot({ path, fullPage: true });
  console.log(`screenshot ${path}`);
}

await page.goto(`${frontend}/login`, { waitUntil: "networkidle" });
await page.getByRole("heading", { name: "Welcome to SynfoTalent" }).waitFor();
await shot("01-login");

await page.getByLabel("Username").fill(username);
await page.getByLabel("Password").fill(password);
await page.getByRole("button", { name: "Sign in" }).click();
await page.getByRole("heading", { name: "Good work starts with visibility." }).waitFor();
await shot("02-dashboard-after-login");

await page.getByRole("link", { name: "Candidates" }).click();
await page.getByRole("heading", { name: "Candidates" }).waitFor();
const consent = page.getByRole("checkbox", { name: /Candidate has given consent/ });
await consent.waitFor();
await shot("03-candidate-form-consent-visible");

await page.getByPlaceholder("Full name").fill("Browser Candidate");
await page.getByPlaceholder("Privacy notice version").fill("notice-browser");
await page.getByRole("button", { name: "Save candidate" }).click();
const blocked = await page.evaluate(() => {
  const box = document.querySelector('input[type="checkbox"]');
  return box ? !box.checked && !box.validity.valid : false;
});
if (!blocked) throw new Error("Consent checkbox did not block submit");
await shot("04-consent-required-blocks-submit");

await consent.check();
await page.getByRole("button", { name: "Save candidate" }).click();
await page.getByText("Browser Candidate").waitFor();
await shot("05-candidate-saved-with-consent");

const issued = await page.evaluate(async (apiUrl) => {
  const refresh = localStorage.getItem("refresh");
  const before = localStorage.getItem("access");
  localStorage.setItem("access", "not-a-valid-access-token");
  const response = await fetch(`${apiUrl}/candidates/`, {
    headers: { Authorization: "Bearer not-a-valid-access-token" },
  });
  return { refreshPresent: Boolean(refresh), beforeStarts: before?.slice(0, 20), unauthenticatedStatus: response.status };
}, api);
console.log("pre-refresh probe", JSON.stringify(issued));

await page.reload({ waitUntil: "networkidle" });
await page.getByRole("heading", { name: "Candidates" }).waitFor();
await page.getByText("Browser Candidate").waitFor({ timeout: 15000 });
const after = await page.evaluate(() => localStorage.getItem("access"));
if (!after || after === "not-a-valid-access-token" || after.split(".").length !== 3) {
  throw new Error(`access token was not refreshed: ${after}`);
}
console.log("access token refreshed", after.slice(0, 24));
await shot("06-page-loaded-after-token-refresh");

await browser.close();
console.log("browser verification ok");
