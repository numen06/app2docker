from pathlib import Path
import re

p = Path(__file__).parent / "migrate-shadcn.py"
t = p.read_text(encoding="utf-8")
new_fn = '''def patch_agent_tabs(tpl):
    s = tpl.find('        <ul class="nav nav-tabs nav-tabs-custom mb-0"')
    if s < 0:
        return tpl
    s = tpl.rfind('    <motion-icon>', 0, s)
    s = tpl.rfind('    <div class="card mb-3">', 0, s)
    e = tpl.find('    <!-- \u4e3b\u673a\u5217\u8868\u6807\u7b7e\u9875 -->', s)
    new = """    <Card class="mb-3">
      <CardContent class="p-2">
        <div class="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1" role="tablist">
          <button type="button" class="rounded-md px-4 py-2 text-sm font-medium transition" :class="activeTab === 'hosts' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'" @click="activeTab = 'hosts'"><i class="fas fa-server mr-1"></i> \u4e3b\u673a\u5217\u8868</button>
          <button type="button" class="rounded-md px-4 py-2 text-sm font-medium transition" :class="activeTab === 'secrets' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'" @click="activeTab = 'secrets'"><i class="fas fa-key mr-1"></i> \u5bc6\u94a5\u7ba1\u7406</button>
          <button type="button" class="rounded-md px-4 py-2 text-sm font-medium transition" :class="activeTab === 'pending' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'" @click="activeTab = 'pending'"><i class="fas fa-clock mr-1"></i> \u5f85\u52a0\u5165\u4e3b\u673a<Badge v-if="pendingHostsCount > 0" variant="danger" class="ml-1">{{ pendingHostsCount }}</Badge></button>
        </div>
      </CardContent>
    </Card>

"""
    new_fn = new_fn.replace("    <motion-icon>", "    <div")
    new_fn = new_fn.replace("tpl.rfind('    <motion-icon>', 0, s)\n    ", "")
    return tpl[:s] + new + tpl[e:]
'''
# fix the broken strings in new_fn - I made errors. Let me write clean version
new_fn = '''def patch_agent_tabs(tpl):
    ul = '        <ul class="nav nav-tabs nav-tabs-custom mb-0"'
    s = tpl.find(ul)
    if s < 0:
        return tpl
    s = tpl.rfind('    <div class="card mb-3">', 0, s)
    e = tpl.find('    <!-- \u4e3b\u673a\u5217\u8868\u6807\u7b7e\u9875 -->', s)
    new = """    <Card class="mb-3">
      <CardContent class="p-2">
        <motion-icon>
        <motion-icon>
        <div class="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1" role="tablist">
          <button type="button" class="rounded-md px-4 py-2 text-sm font-medium transition" :class="activeTab === 'hosts' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'" @click="activeTab = 'hosts'"><i class="fas fa-server mr-1"></i> \u4e3b\u673a\u5217\u8868</button>
          <button type="button" class="rounded-md px-4 py-2 text-sm font-medium transition" :class="activeTab === 'secrets' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'" @click="activeTab = 'secrets'"><i class="fas fa-key mr-1"></i> \u5bc6\u94a5\u7ba1\u7406</button>
          <button type="button" class="rounded-md px-4 py-2 text-sm font-medium transition" :class="activeTab === 'pending' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'" @click="activeTab = 'pending'"><i class="fas fa-clock mr-1"></i> \u5f85\u52a0\u5165\u4e3b\u673a<Badge v-if="pendingHostsCount > 0" variant="danger" class="ml-1">{{ pendingHostsCount }}</Badge></button>
        </div>
      </CardContent>
    </Card>

"""
    return tpl[:s] + new + tpl[e:]
'''
# remove motion-icon lines from new string
new_fn = new_fn.replace('        <motion-icon>\n        <motion-icon>\n        ', '        ')
t2 = re.sub(r"def patch_agent_tabs\(tpl\):.*?return tpl\[:s\] \+ new \+ tpl\[e:\]", new_fn.strip(), t, flags=re.DOTALL)
p.write_text(t2, encoding="utf-8")
print("fixed")
