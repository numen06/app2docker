const fs = require("fs");
const path = require("path");
const root = path.join(__dirname, "..", "frontend");
const { parse } = require(path.join(root, "node_modules/@vue/compiler-dom"));
const lines = fs
  .readFileSync(path.join(root, "src/components/DeployTaskManager.vue"), "utf8")
  .match(/<template>([\s\S]*)<\/template>/)[1]
  .split("\n");
for (const end of [1117, 2110, 2138, lines.length - 1]) {
  const c = lines.slice(0, end).join("\n") + "\n</div>";
  try {
    parse(c);
    console.log("OK", end);
  } catch (e) {
    console.log("FAIL", end, e.message, "line", e.loc?.start?.line);
    break;
  }
}
