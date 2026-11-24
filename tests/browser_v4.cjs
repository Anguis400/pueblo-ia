/* Run against a repository subpath, like GitHub Pages. No third-party service is called. */
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const http = require("node:http");
const path = require("node:path");
const { chromium } = require("playwright");
const SITE = path.resolve(__dirname, "../site");
const PREFIX = "/pueblo-ia/";
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css",
  ".js": "text/javascript",
  ".json": "application/json",
  ".zip": "application/zip",
};

(async () => {
  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, "http://localhost");
      if (!url.pathname.startsWith(PREFIX))
        throw Error("Outside Pages subpath");
      const relative = decodeURIComponent(url.pathname.slice(PREFIX.length));
      let target = path.resolve(SITE, relative || ".");
      if (target !== SITE && !target.startsWith(SITE + path.sep))
        throw Error("Invalid path");
      if ((await fs.stat(target)).isDirectory())
        target = path.join(target, "index.html");
      res.setHeader(
        "Content-Type",
        TYPES[path.extname(target)] || "application/octet-stream",
      );
      res.end(await fs.readFile(target));
    } catch {
      res.statusCode = 404;
      res.end("Not found");
    }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const base = `http://127.0.0.1:${server.address().port}${PREFIX}`;
  let browser;
  try {
    browser = await chromium.launch({
      headless: true,
      ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
        ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE }
        : {}),
    });
    const page = await browser.newPage({
      viewport: { width: 1536, height: 1050 },
    });
    const errors = [];
    const failed = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("response", (response) => {
      if (response.status() >= 400) failed.push(response.url());
    });
    page.on("request", (request) => {
      if (!request.url().startsWith(base))
        errors.push("Unexpected external request: " + request.url());
    });
    const report = JSON.parse(
      await fs.readFile(path.join(SITE, "data/company.json"), "utf8"),
    );
    for (const width of [1536, 1366, 1024, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 1050 });
      for (const route of ["", "empresa/", "marketing/", "tienda/", "ventas/"]) {
        const response = await page.goto(base + route);
        assert.equal(response.status(), 200);
        assert.equal(
          await page.evaluate(
            () => document.documentElement.scrollWidth > innerWidth + 1,
          ),
          false,
          `Page overflow at ${width}px: ${route}`,
        );
        // Every relative file and route on the page must work below /pueblo-ia/.
        const links = await page
          .locator("a[href]")
          .evaluateAll((nodes) => [
            ...new Set(
              nodes.map(
                (n) => new URL(n.getAttribute("href"), document.baseURI).href,
              ),
            ),
          ]);
        for (const link of links.filter((url) => url.startsWith(base))) {
          const res = await page.request.get(link.split("#")[0]);
          assert.equal(res.status(), 200, link);
        }
      }
    }
    await page.goto(base + "ventas/");
    assert.ok((await page.locator("body").innerText()).includes("no envía mensajes"));
    assert.equal(await page.locator('meta[name="robots"]').getAttribute("content"), "noindex");
    await page.setViewportSize({ width: 1536, height: 1050 });
    await page.goto(base + "empresa/");
    assert.equal(await page.locator(".building").count(), 7);
    assert.equal(
      await page.locator(".role-card").count(),
      report.agents.length,
    );
    const expected = {
      productos: String(
        report.catalog.filter((p) => p.state === "demo_funcional").length,
      ),
      compradores: String(
        report.agents.find((a) => a.agent === "demanda").result.buyer_signals,
      ),
      ventas:
        report.agents.find((a) => a.agent === "conversion").result
          .verified_sales === null
          ? "—"
          : String(
              report.agents.find((a) => a.agent === "conversion").result
                .verified_sales,
            ),
    };
    for (const [key, value] of Object.entries(expected)) {
      assert.equal(
        (
          await page.locator(`[data-kpi="${key}"] .kpi-value`).innerText()
        ).trim(),
        value,
      );
    }
    for (const zone of [
      "direccion",
      "inteligencia",
      "producto",
      "marketing",
      "ventas",
      "clientes",
      "finanzas",
    ]) {
      await page.locator(`.building[data-department="${zone}"]`).click();
      assert.equal(
        await page
          .locator(".department-panel:visible")
          .getAttribute("data-panel"),
        zone,
      );
      assert.equal(
        await page.locator(".department-panel:visible .role-card").count(),
        3,
      );
      const card = page.locator(".department-panel:visible .role-card").first();
      await card.locator("summary").first().click();
      assert.equal(await card.evaluate((node) => node.open), true);
      const evidence = card.locator(".role-body > a").first();
      const res = await page.request.get(
        await evidence.evaluate((node) => node.href),
      );
      assert.equal(res.status(), 200);
      const artifact = await res.json();
      assert.equal(artifact.agent, await card.getAttribute("id"));
    }
    // SVG buildings are native keyboard-operable links.
    await page.locator('.building[data-department="inteligencia"]').focus();
    await page.keyboard.press("Enter");
    await page.waitForFunction(
      () =>
        document.querySelector('[data-panel="inteligencia"]').hidden === false,
    );
    await page.locator("#all-roles").click();
    assert.equal(
      await page.locator(".department-panel:visible .role-card").count(),
      21,
    );
    await page.locator("#all-roles").click();
    assert.equal(
      await page
        .locator(".department-panel:visible")
        .getAttribute("data-panel"),
      "producto",
    );
    await page.goto(base + "empresa/#ceo");
    assert.equal(await page.locator("#ceo").isVisible(), true);
    assert.equal(
      await page.locator("#ceo").evaluate((node) => node.open),
      true,
    );
    await page.locator('.zone-shortcut[data-department="ventas"]').click();
    await page.goBack();
    assert.equal(
      await page.locator('[data-panel="direccion"]').isVisible(),
      true,
    );
    const motion = page.locator("#motion-toggle");
    await motion.click();
    assert.equal(await motion.getAttribute("aria-pressed"), "true");
    assert.equal(
      await page
        .locator(".village-panel")
        .evaluate((node) => node.classList.contains("motion-paused")),
      true,
    );
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.waitForFunction(
      () => document.querySelector("#motion-toggle").disabled,
    );
    assert.equal(
      await page
        .locator(".courier")
        .first()
        .evaluate((node) => getComputedStyle(node).animationName),
      "none",
    );
    // Mobile shortcuts bring the correct three roles into view without page overflow.
    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator('.zone-shortcut[data-department="clientes"]').click();
    assert.equal(
      await page.locator('[data-panel="clientes"]').isVisible(),
      true,
    );
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth + 1,
      ),
      false,
    );
    // Existing demos retain working calculations and remain independent of audited KPIs.
    for (const [slug, values, expected] of [
      ["escandallo", { coste: 10, horas: 2, tarifa: 20, margen: 50 }, "100,00"],
      [
        "presupuesto",
        { horas: 2, tarifa: 20, extras: 10, impuesto: 21 },
        "60,50",
      ],
      ["rentabilidad", { fijos: 100, variable: 5, precio: 15 }, "10"],
      ["conversion", { visitas: 100, consultas: 10, ventas: 2 }, "2.00%"],
    ]) {
      await page.goto(base + "tienda/" + slug + ".html");
      for (const [key, value] of Object.entries(values))
        await page.locator(`[name="${key}"]`).fill(String(value));
      await page.locator("button").click();
      assert.ok((await page.locator("output").innerText()).includes(expected));
    }
    // Public pastry demo: real DOM calculation, invalid inputs, reset and purchase destination.
    for (const width of [1536, 390, 320]) {
      await page.setViewportSize({ width, height: 1050 });
      const res = await page.goto(base + "tienda/escandallo-pro/");
      assert.equal(res.status(), 200);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, "Pastry demo overflow");
      assert.ok((await page.locator("#batch").innerText()).includes("24,00"));
      assert.ok((await page.locator("#unit").innerText()).includes("2,00"));
      assert.ok((await page.locator("#gross").innerText()).includes("5,50"));
      for (const href of await page.locator("a[href]").evaluateAll(nodes => nodes.map(n => n.href)))
        assert.equal(href, "https://payhip.com/b/IiVct");
      await page.locator("#units").fill("6");
      assert.ok((await page.locator("#unit").innerText()).includes("4,00"));
      await page.locator("#units").fill("0");
      assert.equal(await page.locator("#unit").innerText(), "—");
      assert.notEqual(await page.locator("#error").innerText(), "");
      await page.locator('button[type="reset"]').click();
      await page.waitForFunction(() => document.querySelector("#unit").textContent.includes("2,00"));
      await page.locator("#margin").fill("100");
      assert.equal(await page.locator("#gross").innerText(), "—");
      await page.locator("#margin").fill("");
      assert.equal(await page.locator("#gross").innerText(), "—");
    }
    await page.goto(base + "radar/");
    assert.equal(
      await page.locator("#leads").innerText(),
      String(
        JSON.parse(
          await fs.readFile(path.join(SITE, "data/latest.json"), "utf8"),
        ).opportunities.length,
      ),
    );
    assert.ok(
      (
        await page.locator('a[href="./empresa/"]').evaluate((node) => node.href)
      ).includes("/pueblo-ia/empresa/"),
    );
    const noJS = await browser.newContext({ javaScriptEnabled: false });
    const fallback = await noJS.newPage();
    await fallback.goto(base + "empresa/");
    assert.equal(await fallback.locator(".role-card").count(), 21);
    assert.equal(
      await fallback.locator(".department-panel:visible").count(),
      7,
    );
    await fallback.locator('.building[data-department="finanzas"]').click();
    assert.ok(fallback.url().endsWith("#departamento-finanzas"));
    await noJS.close();
    assert.deepEqual(errors, []);
    assert.deepEqual(failed, []);
    console.log(
      "PASS: 5 pages × 6 viewport sizes below /pueblo-ia/, 7 buildings, 21 roles, real KPI/evidence links, keyboard/history, reduced motion, no-JS fallback, radar and 4 calculators.",
    );
  } finally {
    if (browser) await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
