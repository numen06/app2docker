#!/usr/bin/env python3
import re
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components" / "DockerManager.vue"
t = p.read_text(encoding="utf-8")
t = t.replace('class="row g-2"', 'class="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6"')
t = re.sub(r'\n\s*<div class="col-6 col-md-2"[^>]*>\n', "\n", t)
# Remove extra closing div after info-item (was col wrapper)
t = re.sub(
    r'(            </div>\n)(          </div>\n)(          (?:<!--|<motion.div class="info-item"|<div class="info-item"))',
    r"\1\3",
    t,
)
t = re.sub(
    r'(            </motion.div>\n)(          </div>\n)(          (?:<!--|<div class="info-item"))',
    r"\1\3",
    t,
)
p.write_text(t, encoding="utf-8")
print("ok")
