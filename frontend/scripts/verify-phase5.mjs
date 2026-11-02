import { mkdir } from "node:fs/promises";
import { chromium } from "playwright-core";

const frontend = process.env.FRONTEND_URL || "http://localhost:5173";
const outDir = process.env.SCREENSHOT_DIR || "/opt/cursor/artifacts/screenshots";
const password = process.env.VERIFY_PASSWORD || "longpassword1";

const browser = await chromium.launch({
  executablePath: process.env.CHROME_PATH || "/usr/bin/google-chrome",
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

await signIn("hrphase5");
await page.getByText("Invoiced revenue").waitFor({ state: "hidden" });
if (await page.getByRole("link", { name: "Billing" }).count()) {
  throw new Error("HR navigation includes Billing");
}
await shot("phase5-hr-dashboard");

await page.goto(`${frontend}/billing`, { waitUntil: "networkidle" });
await page.getByText("You do not have permission to view this page.").waitFor();
await shot("phase5-hr-billing-denied");

await page.getByRole("link", { name: "Placements" }).click();
await page.getByRole("heading", { name: "Placements" }).waitFor();
await page.getByText("Has Python").waitFor();
const hrPlacement = await page.locator("body").innerText();
if (hrPlacement.includes("880011") || hrPlacement.includes("8,80,011") || hrPlacement.includes("Offered CTC")) {
  throw new Error("HR placement page shows financial fields");
}
await shot("phase5-hr-placement");

await page.getByRole("link", { name: "Pipeline" }).click();
await page.getByRole("heading", { name: "Applications" }).waitFor();
const identified = page.locator("article").filter({ hasText: "SW-CAN-00001" });
await identified.getByRole("button", { name: "Contacted" }).click();
const contactedColumn = page.locator("section").filter({ has: page.getByRole("heading", { name: /^Contacted/ }) });
await contactedColumn.locator("article").filter({ hasText: "SW-CAN-00001" }).waitFor();
await shot("phase5-hr-pipeline-contacted");

await page.getByRole("link", { name: "Candidates" }).click();
const candidateName = `Consent Candidate ${Date.now()}`;
await page.getByPlaceholder("Full name").fill(candidateName);
await page.getByPlaceholder("Privacy notice version").fill("notice-phase5");
await page.getByRole("button", { name: "Save candidate" }).click();
const blocked = await page.evaluate(() => {
  const box = document.querySelector('input[type="checkbox"]');
  return box ? !box.checked && !box.validity.valid : false;
});
if (!blocked) throw new Error("Consent checkbox did not block submit");
await page.getByRole("checkbox", { name: /Candidate has given consent/ }).check();
await page.getByRole("button", { name: "Save candidate" }).click();
await page.getByRole("cell", { name: candidateName }).waitFor();
await shot("phase5-hr-candidate-consent");

await page.getByRole("link", { name: "Duplicate review" }).click();
await page.getByRole("heading", { name: /Missing Skill Copy/ }).waitFor();
await page.getByRole("button", { name: "Approve" }).click();
await page.getByText(/does not merge or delete/i).waitFor();
await page.getByText(/were not merged/i).waitFor();
await shot("phase5-hr-duplicate-approved");

await page.getByRole("link", { name: "Job descriptions" }).click();
await page.getByRole("button", { name: "Find candidates" }).click();
await page.getByText(/Missing mandatory skills: Python/i).first().waitFor();
await shot("phase5-hr-match-explanation");

await signOut();
await signIn("salesphase5");
await page.getByRole("link", { name: "Job descriptions" }).click();
await page.getByText("Backend Engineer").waitFor();
if (await page.getByRole("button", { name: "Find candidates" }).count()) {
  throw new Error("Sales can see Find candidates");
}
await shot("phase5-sales-match-hidden");

await signOut();
await signIn("mgmtphase5");
await page.getByText("Invoiced revenue").waitFor();
await shot("phase5-management-dashboard");
await page.getByRole("link", { name: "Placements" }).click();
await page.getByText(/8,80,011\.22|880,011\.22/).waitFor();
await page.getByText(/7,70,022\.33|770,022\.33/).waitFor();
await shot("phase5-management-placement");
await page.getByRole("link", { name: "Billing" }).click();
await page.getByRole("cell", { name: "SW-INV-2026-0001" }).waitFor();
await page.getByText(/6,54,321\.09|654,321\.09/).first().waitFor();
await shot("phase5-management-billing");

await browser.close();
console.log("phase 5 browser verification ok");
