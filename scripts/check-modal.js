const fs = require("fs");
const path = require("path");
const root = path.join(__dirname, "..", "frontend");
const { parse } = require(path.join(root, "node_modules/@vue/compiler-dom"));
const lines = fs
  .readFileSync(path.join(root, "src/components/DeployTaskManager.vue"), "utf8")
  .match(/<template>([\s\S]*)<\/template>/)[1]
  .split("\n");
const c = lines.slice(1117, 2110).join("\n");
try {
  parse("<motion>" + c + "</motion>");
  console.log("edit OK");
} catch (e) {
  const ln = e.loc?.start?.line;
  const ls = ("<motion>\n" + c).split("\n");
  console.log(e.message, "line", ln, "file", 1117 + ln);
  for (let i = Math.max(0, ln - 3); i < Math.min(ls.length, ln + 3); i++) {
    console.log(i + 1, ls[i]);
  }
}
