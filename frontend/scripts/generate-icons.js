#!/usr/bin/env node
/**
 * Generates PWA icon files from logo.png.
 * No external dependencies — runs during Docker build.
 * Requires sharp (bundled with Next.js in production).
 * Falls back to copying logo.png as-is if sharp is unavailable.
 */
const path = require("path");
const fs = require("fs");

const publicDir = path.join(__dirname, "../public");
const iconsDir = path.join(publicDir, "icons");
const logoPath = path.join(publicDir, "logo.png");

if (!fs.existsSync(logoPath)) {
  console.warn("⚠  logo.png not found — skipping icon generation");
  process.exit(0);
}

if (!fs.existsSync(iconsDir)) {
  fs.mkdirSync(iconsDir, { recursive: true });
}

const sizes = [
  { name: "icon-192.png",       size: 192, bg: { r: 255, g: 255, b: 255, alpha: 1 } },
  { name: "icon-512.png",       size: 512, bg: { r: 255, g: 255, b: 255, alpha: 1 } },
  { name: "icon-maskable.png",  size: 512, bg: { r: 10,  g: 22,  b: 40,  alpha: 1 } },
  { name: "apple-touch-icon.png", size: 180, bg: { r: 255, g: 255, b: 255, alpha: 1 } },
];

async function withSharp() {
  const sharp = require("sharp");
  for (const { name, size, bg } of sizes) {
    await sharp(logoPath)
      .resize(size, size, { fit: "contain", background: bg })
      .png()
      .toFile(path.join(iconsDir, name));
    console.log(`  ✓ icons/${name}`);
  }
}

function fallbackCopy() {
  const logo = fs.readFileSync(logoPath);
  for (const { name } of sizes) {
    fs.writeFileSync(path.join(iconsDir, name), logo);
    console.log(`  ✓ icons/${name} (copy)`);
  }
}

(async () => {
  console.log("Generating PWA icons...");
  try {
    await withSharp();
  } catch {
    console.log("  sharp unavailable — using copy fallback");
    fallbackCopy();
  }
  console.log("PWA icons ready.");
})();
