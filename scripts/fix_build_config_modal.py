from pathlib import Path

p = Path("frontend/src/components/BuildConfigEditor.vue")
t = p.read_text(encoding="utf-8")
start = t.index("    <!-- JSON")
end = t.index("  </div>\n</template>", start)
cd = "</" + "motionless-host-manager />"
# build close tag without autocomplete issues
cd = "</" + "div>"

new = f"""    <FormDialog v-model="showJsonModal" title="构建配置 JSON" icon="fa-code" size="lg">
      <div class="mb-2 flex justify-end">
        <Button type="button" variant="outline" size="sm" @click="copyJson">
          <i class="fas fa-copy"></i> 复制 JSON
        </Button>
      {cd}
      <codemirror
        v-model="configJsonText"
        :style="{{ height: '500px', fontSize: '13px' }}"
        :disabled="true"
        :extensions="jsonEditorExtensions"
      />
      <template #footer>
        <Button variant="outline" type="button" @click="showJsonModal = false">关闭</Button>
      </template>
    </FormDialog>
"""

p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("done")
