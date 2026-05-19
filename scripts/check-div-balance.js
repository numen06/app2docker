const fs = require("fs");
const path = require("path");
const root = path.join(__dirname, "..", "frontend");
const { parse } = require(path.join(root, "node_modules/@vue/compiler-dom"));
const s = fs.readFileSync(
  path.join(root, "src/components/DeployTaskManager.vue"),
  "utf8"
);
const t = s.match(/<template>([\s\S]*)<\/template>/)[1];
try {
  parse(t);
  console.log("FULL TEMPLATE OK");
} catch (e) {
  console.log("Error:", e.message);
  console.log("Line:", e.loc?.start?.line);
  const lines = t.split("\n");
  const line = e.loc?.start?.line;
  if (line) {
    for (let i = Math.max(0, line - 4); i < Math.min(lines.length, line + 4); i++) {
      console.log(String(i + 1).padStart(4), lines[i]);
    }
  }
}
