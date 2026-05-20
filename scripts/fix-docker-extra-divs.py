#!/usr/bin/env python3
import re
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components" / "DockerManager.vue"
t = p.read_text(encoding="utf-8")
t = re.sub(
    r"(\n            </motion.div>)\n          </motion.div>(?=\n            <div class=\"info-item\">)",
    r"\1",
    t,
)
t = re.sub(
    r"(\n            </motion.div>)\n          </motion.div>(?=\n\n          <!--)",
    r"\1",
    t,
)
t = re.sub(
    r"(\n            </motion.div>)\n          </motion.div>(?=\n        </motion.div>)",
    r"\1",
    t,
)
# fix if still using </motion.div> for info-item - file uses </motion.div> for info-item inner
t = re.sub(
    r"(\n            </div>)\n          </div>(?=\n            <div class=\"info-item\">)",
    r"\1",
    t,
)
t = re.sub(
    r"(\n            </div>)\n          </div>(?=\n\n          <!--)",
    r"\1",
    t,
)
t = re.sub(
    r"(\n            </div>)\n          </div>(?=\n        </div>)",
    r"\1",
    t,
)
p.write_text(t, encoding="utf-8")
print("fixed")
