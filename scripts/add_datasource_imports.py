import re
from pathlib import Path

p = Path("frontend/src/components/DataSourcePanel.vue")
t = p.read_text(encoding="utf-8")
imp = """import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import Card from "@/components/ui/card/Card.vue";
import CardHeader from "@/components/ui/card/CardHeader.vue";
import CardTitle from "@/components/ui/card/CardTitle.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import { Badge } from "@/components/ui/badge";
"""
if "@/components/ui/card/Card.vue" not in t:
    t = t.replace("import PageToolbar", imp + "import PageToolbar", 1)
t = re.sub(r"\n<style scoped>.*?</style>\s*$", "\n", t, flags=re.DOTALL)
p.write_text(t, encoding="utf-8")
print("ok")
