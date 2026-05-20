import re
from pathlib import Path

p = Path("frontend/src/components/BuildConfigEditor.vue")
t = p.read_text(encoding="utf-8")
imp = """import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import Card from "@/components/ui/card/Card.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
"""
if "@/components/ui/button/Button.vue" not in t:
    t = t.replace("import axios", imp + "import axios", 1)
t = re.sub(r"\n<style scoped>.*?</style>\s*$", "\n", t, flags=re.DOTALL)
p.write_text(t, encoding="utf-8")
print("ok")
