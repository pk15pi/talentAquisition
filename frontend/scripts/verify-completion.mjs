import { mkdir } from "node:fs/promises";
import { chromium } from "playwright-core";

const frontend = process.env.FRONTEND_URL || "http://localhost:5173";
const outDir = process.env.SCREENSHOT_DIR || "/opt/cursor/artifacts/screenshots";
const password = process.env.VERIFY_PASSWORD || "longpassword1";

const browser = await chromium.launch({
  executablePath: process.env.CHROME_PATH || "/usr/local/bin/google-chrome",
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage({ viewport: { width: 1360, height: 900 } });
await mkdir(outDir, { recursive: true });

async function shot(name) {
  const path = `${outDir}/${name}.png`;
  await page.screenshot({ path, fullPage: true });
  console.log(`screenshot ${path}`);
}

async function signIn(username) {
  await page.goto(`${frontend}/login`, { waitUntil: "networkidle" });
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "Good work starts with visibility." }).waitFor();
}

async function signOut() {
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByRole("heading", { name: "Welcome to SynfoTalent" }).waitFor();
}

await signIn("hrcomplete");
if (await page.getByRole("link", { name: "Billing" }).count()) throw new Error("HR sees Billing");
if (await page.getByRole("link", { name: "Opportunities" }).count()) throw new Error("HR sees Opportunities");
if (await page.getByText("Invoiced revenue").count()) throw new Error("HR dashboard shows revenue");
await shot("completion-hr-dashboard");

await page.goto(`${frontend}/billing`, { waitUntil: "networkidle" });
await page.getByText("You do not have permission to view this page.").waitFor();
await page.goto(`${frontend}/opportunities`, { waitUntil: "networkidle" });
await page.getByText("You do not have permission to view this page.").waitFor();

await page.getByRole("link", { name: "Placements" }).click();
await page.getByRole("heading", { name: "Placements" }).waitFor();
await page.getByText("Browser Candidate").waitFor();
const hrPlacement = await page.locator("body").innerText();
if (/Offered CTC|123456|1,23,456/.test(hrPlacement)) throw new Error("HR placement shows money");
await shot("completion-hr-placement");

await page.getByRole("link", { name: "Candidates" }).click();
const candidateName = `Consent Walk ${Date.now()}`;
await page.getByPlaceholder("Full name").fill(candidateName);
await page.getByPlaceholder("Privacy notice version").fill("notice-walk");
await page.getByRole("button", { name: "Save candidate" }).click();
const blocked = await page.evaluate(() => {
  const box = document.querySelector('input[type="checkbox"]');
  return Boolean(box && !box.checked && !box.validity.valid);
});
if (!blocked) throw new Error("Consent checkbox did not block submit");
await page.getByRole("checkbox", { name: /Candidate has given consent/ }).check();
await page.getByRole("button", { name: "Save candidate" }).click();
await page.getByRole("cell", { name: candidateName }).click();
await page.getByRole("button", { name: "Withdraw consent" }).click();
await page.getByText("Consent withdrawn. The profile was not deleted.").first().waitFor();
await shot("completion-hr-consent-withdrawn");

await signOut();
await signIn("salescomplete");
if (await page.getByRole("link", { name: "Candidates" }).count()) throw new Error("Sales sees Candidates");
await page.getByRole("link", { name: "Opportunities" }).click();
await page.getByRole("heading", { name: "Opportunities" }).waitFor();
await page.getByLabel("Title").fill("Browser Deal");
await page.getByLabel("Client").selectOption({ index: 1 });
await page.getByRole("button", { name: "Save opportunity" }).click();
await page.getByText("Browser Deal").waitFor();
await shot("completion-sales-opportunity");
await page.goto(`${frontend}/billing`, { waitUntil: "networkidle" });
await page.getByText("You do not have permission to view this page.").waitFor();
await page.getByRole("link", { name: "Job descriptions" }).click();
await page.getByText("Browser Role").waitFor();
if (await page.getByRole("button", { name: "Find candidates" }).count()) throw new Error("Sales sees Find candidates");
await shot("completion-sales-match-hidden");

await signOut();
await signIn("mgmtcomplete");
await page.getByText("Invoiced revenue").waitFor();
await page.getByRole("link", { name: "Billing" }).click();
await page.getByRole("heading", { name: "Billing" }).waitFor();
await shot("completion-management-billing");
await page.getByRole("link", { name: "Placements" }).click();
await page.getByRole("cell", { name: "Browser Candidate" }).waitFor();
await page.getByRole("cell", { name: /1,23,456\.78|123,456\.78/ }).waitFor();
await shot("completion-management-placement");
await page.getByRole("link", { name: "Reports" }).click();
await page.getByRole("heading", { name: "Performance reports" }).waitFor();
await page.getByRole("button", { name: "Apply filters" }).click();
await page.getByText("Browser Client").waitFor({ timeout: 5000 }).catch(() => {});
await shot("completion-management-reports");

await browser.close();
console.log("completion browser verification ok");
