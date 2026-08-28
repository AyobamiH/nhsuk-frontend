import fs from "node:fs/promises"
import path from "node:path"

import { chromium, webkit } from "playwright-core"

const outputDir = process.env.EVIDENCE_DIR
const browserMatrix = JSON.parse(process.env.BROWSER_MATRIX ?? "[]")

if (!outputDir || browserMatrix.length === 0) {
  throw new Error("EVIDENCE_DIR and BROWSER_MATRIX are required")
}

const url =
  "http://127.0.0.1:3000/nhsuk-frontend/components/" +
  "checkboxes/small-with-pre-checked-values/"
const selector = ".nhsuk-checkboxes--small .nhsuk-checkboxes__input:checked"

const variants = [
  {
    name: "legacy-pre-v10.6",
    declarations: [
      "top: 1.125rem",
      "left: 0.5rem",
      "width: 0.75rem",
      "height: 0.375rem",
      "transform: rotate(-45deg)"
    ]
  },
  {
    name: "current",
    declarations: ["transform: rotate(-45deg) translate(-50%, -50%)"]
  },
  {
    name: "fixed-minus-0.25px",
    declarations: [
      "transform: translateX(-0.25px) rotate(-45deg) translate(-50%, -50%)"
    ]
  },
  {
    name: "fixed-minus-0.5px",
    declarations: [
      "transform: translateX(-0.5px) rotate(-45deg) translate(-50%, -50%)"
    ]
  },
  {
    name: "fixed-minus-0.75px",
    declarations: [
      "transform: translateX(-0.75px) rotate(-45deg) translate(-50%, -50%)"
    ]
  },
  {
    name: "candidate-rem-minus-0.03125",
    declarations: [
      "transform: translateX(-0.03125rem) rotate(-45deg) translate(-50%, -50%)"
    ]
  }
]

const scenarios = [
  { name: "default-text", rootFontSize: "100%", scaleFactors: [1, 1.25, 1.5, 2] },
  { name: "text-200-percent", rootFontSize: "200%", scaleFactors: [1, 2] }
]

const browserTypes = { chromium, webkit }

await fs.mkdir(outputDir, { recursive: true })
const records = []
const forcedColourStates = []

for (const browserSpec of browserMatrix) {
  const browserType = browserTypes[browserSpec.engine]
  if (!browserType) {
    throw new Error(`Unsupported browser engine: ${browserSpec.engine}`)
  }

  const browser = await browserType.launch({
    channel: browserSpec.channel,
    headless: true
  })

  try {
    for (const scenario of scenarios) {
      for (const deviceScaleFactor of scenario.scaleFactors) {
        const context = await browser.newContext({
          deviceScaleFactor,
          viewport: { width: 1200, height: 900 }
        })
        const page = await context.newPage()
        await page.goto(url, { waitUntil: "networkidle" })

        for (const variant of variants) {
          await applyVariant(page, scenario, variant, true)
          const input = page.locator(selector).first()
          if ((await input.count()) !== 1) {
            throw new Error(`Expected one checked small checkbox in ${browserSpec.name}`)
          }
          await input.focus()
          await page.evaluate(() => new Promise(requestAnimationFrame))

          const inputBox = await input.boundingBox()
          if (!inputBox) {
            throw new Error("Small checkbox input has no bounding box")
          }

          const filename = [
            browserSpec.name,
            scenario.name,
            `dpr-${String(deviceScaleFactor).replace(".", "-")}`,
            variant.name
          ].join("-") + ".png"

          await page.screenshot({
            path: path.join(outputDir, filename),
            clip: clipFor(inputBox)
          })
          records.push({
            browser: browserSpec.name,
            deviceScaleFactor,
            filename,
            scenario: scenario.name,
            variant: variant.name
          })
        }

        await context.close()
      }
    }

    const context = await browser.newContext({
      deviceScaleFactor: 1,
      viewport: { width: 1200, height: 900 }
    })
    const page = await context.newPage()
    await page.emulateMedia({ forcedColors: "active" })
    await page.goto(url, { waitUntil: "networkidle" })

    const candidate = variants.find((variant) =>
      variant.name.startsWith("candidate-")
    )
    await applyVariant(page, scenarios[0], candidate, false)
    const input = page.locator(selector).first()
    await input.focus()
    await page.evaluate(() => new Promise(requestAnimationFrame))
    const inputBox = await input.boundingBox()
    if (!inputBox) {
      throw new Error("Forced-colours checkbox has no bounding box")
    }

    const forcedFilename = `${browserSpec.name}-forced-colours-candidate.png`
    await page.screenshot({
      path: path.join(outputDir, forcedFilename),
      clip: clipFor(inputBox)
    })
    const forcedState = await page.evaluate((inputSelector) => {
      const checkedInput = document.querySelector(inputSelector)
      const label = checkedInput?.nextElementSibling
      if (!label) {
        throw new Error("Unable to resolve forced-colours checkbox label")
      }
      const style = getComputedStyle(label, "::after")
      return {
        borderBottomColor: style.borderBottomColor,
        borderBottomStyle: style.borderBottomStyle,
        borderBottomWidth: style.borderBottomWidth,
        borderLeftColor: style.borderLeftColor,
        borderLeftStyle: style.borderLeftStyle,
        borderLeftWidth: style.borderLeftWidth,
        opacity: style.opacity,
        transform: style.transform
      }
    }, selector)
    forcedColourStates.push({
      browser: browserSpec.name,
      filename: forcedFilename,
      ...forcedState
    })
    await context.close()
  } finally {
    await browser.close()
  }
}

await fs.writeFile(
  path.join(outputDir, "records.json"),
  JSON.stringify(records, null, 2)
)
await fs.writeFile(
  path.join(outputDir, "forced-colours.json"),
  JSON.stringify(forcedColourStates, null, 2)
)

function clipFor(box) {
  return {
    x: Math.max(0, Math.floor(box.x)),
    y: Math.max(0, Math.floor(box.y)),
    width: Math.ceil(box.width),
    height: Math.ceil(box.height)
  }
}

async function applyVariant(page, scenario, variant, useEvidenceColour) {
  await page.evaluate(
    ({ declarations, rootFontSize, useEvidenceColour }) => {
      let style = document.querySelector("#alignment-evidence")
      if (!style) {
        style = document.createElement("style")
        style.id = "alignment-evidence"
        document.head.append(style)
      }

      const colourRule = useEvidenceColour
        ? "border-color: #e60000 !important;"
        : ""
      style.textContent = `
        html { font-size: ${rootFontSize} !important; }
        .nhsuk-checkboxes--small .nhsuk-checkboxes__label::after {
          ${declarations.map((declaration) => `${declaration} !important;`).join("\n")}
          ${colourRule}
        }
      `
    },
    {
      declarations: variant.declarations,
      rootFontSize: scenario.rootFontSize,
      useEvidenceColour
    }
  )
}
