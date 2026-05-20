import re
from pathlib import Path

p = Path("frontend/src/components/HostManager.vue")
t = p.read_text(encoding="utf-8")

t = t.replace(
    """    <div v-if="loading" class="text-center py-12">
      <i class="fas fa-spinner fa-spin"></i> 加载中...
    </div>
    <motionless-host-manager />""",
    "",
)
if "EmptyState" not in t[:800]:
    t = t.replace(
        "    <!-- 主机列表 - 卡片式布局 -->",
        """    <div v-if="loading" class="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
      <i class="fas fa-spinner fa-spin"></i> 加载中…
    </div>
    <EmptyState v-else-if="filteredHosts.length === 0" message="暂无 SSH 主机" icon="fa-server" />""",
        1,
    )

start = t.index('      <div\n        v-for="host in filteredHosts"')
end = t.index("\n\n    <!-- 添加/编辑主机模态框 -->", start)

new = r'''      <Card
        v-for="host in filteredHosts"
        :key="host.host_id"
        class="flex h-full flex-col transition hover:-translate-y-0.5 hover:shadow-md"
      >
        <CardHeader class="space-y-3 border-b border-slate-100 pb-3">
          <CardTitle class="text-base">{{ host.name }}</CardTitle>
          <motionless-host-manager />
          <div class="flex flex-wrap gap-1">
            <Badge variant="default"><i class="fas fa-server"></i> SSH 主机</Badge>
            <Badge v-if="host.has_private_key" variant="info"><i class="fas fa-key"></i> 密钥</Badge>
            <Badge v-else-if="host.has_password" variant="default"><i class="fas fa-lock"></i> 密码</Badge>
            <Badge v-else variant="warning">未配置</Badge>
          </div>
          <p v-if="host.description" class="text-sm text-slate-500">{{ host.description }}</p>
          <div class="flex gap-1">
            <Button
              variant="outline"
              size="sm"
              class="flex-1"
              :disabled="testingConnection === host.host_id"
              title="测试连接"
              @click="testConnection(host)"
            >
              <i v-if="testingConnection === host.host_id" class="fas fa-spinner fa-spin"></i>
              <i v-else class="fas fa-plug"></i>
            </Button>
            <Button variant="outline" size="sm" class="flex-1" title="编辑" @click="editHost(host)">
              <i class="fas fa-edit"></i>
            </Button>
            <Button variant="destructive" size="sm" class="flex-1" title="删除" @click="deleteHost(host)">
              <i class="fas fa-trash"></i>
            </Button>
          </div>
        </CardHeader>
        <CardContent class="space-y-3 p-4 text-sm">
          <div class="flex gap-2 text-slate-600">
            <i class="fas fa-network-wired mt-0.5 w-4 shrink-0 text-slate-400"></i>
            <div>
              <div><strong>{{ host.host }}</strong><span class="text-slate-500">:{{ host.port }}</span></div>
              <div class="mt-1 text-slate-500"><i class="fas fa-user mr-1"></i>{{ host.username }}</div>
            </div>
          </div>
          <div>
            <div v-if="host.checking_docker" class="text-slate-500">
              <i class="fas fa-spinner fa-spin mr-1"></i>检测中…
            </div>
            <template v-else>
              <Badge :variant="host.docker_available ? 'success' : 'default'" class="mb-1">
                <i class="fab fa-docker mr-1"></i>{{ host.docker_available ? "Docker 可用" : "Docker 不可用" }}
              </Badge>
              <p v-if="host.docker_version" class="text-xs text-slate-500">
                <i class="fas fa-info-circle mr-1"></i>{{ host.docker_version }}
              </p>
            </template>
          </div>
          <div class="border-t border-slate-200 pt-2 text-xs text-slate-500">
            <i class="fas fa-clock mr-1"></i>{{ formatTime(host.created_at) }}
          </div>
        </CardContent>
      </Card>
'''
new = new.replace("<motionless-host-manager />\n", "")

t = t[:start] + new + t[end:]

imp = """import FormDialog from '@/components/ui/dialog/FormDialog.vue';
import EmptyState from '@/components/ui/EmptyState.vue';
import AlertBanner from '@/components/ui/AlertBanner.vue';
import Button from '@/components/ui/button/Button.vue';
import Input from '@/components/ui/input/Input.vue';
import Label from '@/components/ui/label/Label.vue';
import Card from '@/components/ui/card/Card.vue';
import CardHeader from '@/components/ui/card/CardHeader.vue';
import CardTitle from '@/components/ui/card/CardTitle.vue';
import CardContent from '@/components/ui/card/CardContent.vue';
import { Badge } from '@/components/ui/badge';

"""
if "FormDialog" not in t:
    t = t.replace("import axios from 'axios';", imp + "import axios from 'axios';", 1)
if "components: {" not in t:
    t = t.replace(
        "  name: 'HostManager',",
        "  name: 'HostManager',\n  components: {\n    FormDialog, EmptyState, AlertBanner, Button, Input, Label,\n    Card, CardHeader, CardTitle, CardContent, Badge,\n  },",
        1,
    )
t = re.sub(r"\n<style scoped>.*?</style>\s*$", "\n", t, flags=re.DOTALL)
p.write_text(t, encoding="utf-8")
print("host cards ok")
