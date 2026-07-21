<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

const CHIP_COLORS = ['--c1', '--c2', '--c3', '--c4', '--c5', '--c6', '--c7', '--c8']

const activeSection = ref('site')
const saving = ref(false)
const toast = ref({ msg: '', type: '' }) // type: 'success' | 'error'
let toastTimer = null

const form = reactive({
  site: { titlePrefix: '', title: '', subtitlePrefix: '', subtitleName: '', pixelText: '' },
  intro: { headline: '', summary: '' },
  skills: [],
  projects: [],
  contact: { email: '', wechat: '', github: '' },
})

// Skills: edit as newline-separated string, preview as chips
const skillsText = computed({
  get: () => form.skills.join('\n'),
  set: (val) => {
    form.skills = val.split('\n').map((s) => s.trim()).filter(Boolean)
  },
})

// Projects: each item in editing form has tags as comma string
const projectForms = ref([])

function projectsToForms(projects) {
  return (projects || []).map((p) => ({
    name: p.name ?? '',
    description: p.description ?? '',
    url: p.url ?? '',
    github: p.github ?? '',
    tags: Array.isArray(p.tags) ? p.tags.join(', ') : (p.tags ?? ''),
  }))
}

function formsToProjects(forms) {
  return forms.map((f) => ({
    name: f.name,
    description: f.description,
    url: f.url,
    github: f.github,
    tags: f.tags.split(',').map((t) => t.trim()).filter(Boolean),
  }))
}

function addProject() {
  projectForms.value.push({ name: '', description: '', url: '', github: '', tags: '' })
}

function removeProject(i) {
  projectForms.value.splice(i, 1)
}

function showToast(msg, type = 'success') {
  toast.value = { msg, type }
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = { msg: '', type: '' } }, 3000)
}

async function fetchContent() {
  const res = await fetch('/api/admin/content')
  const json = await res.json()
  if (json.success) {
    const data = json.data
    Object.assign(form.site, data.site ?? {})
    Object.assign(form.intro, data.intro ?? {})
    form.skills = Array.isArray(data.skills) ? [...data.skills] : []
    form.contact = { ...form.contact, ...(data.contact ?? {}) }
    projectForms.value = projectsToForms(data.projects ?? [])
  }
}

async function saveContent() {
  saving.value = true
  try {
    const payload = {
      site: { ...form.site },
      intro: { ...form.intro },
      skills: [...form.skills],
      projects: formsToProjects(projectForms.value),
      contact: { ...form.contact },
    }
    const res = await fetch('/api/admin/content', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const json = await res.json()
    if (json.success) {
      showToast(json.message || '内容已保存', 'success')
    } else {
      showToast(json.message || '保存失败', 'error')
    }
  } catch {
    showToast('网络错误，请重试', 'error')
  } finally {
    saving.value = false
  }
}

const sections = [
  { key: 'site', label: '站点信息' },
  { key: 'intro', label: '个人简介' },
  { key: 'skills', label: '技能列表' },
  { key: 'projects', label: '项目列表' },
  { key: 'contact', label: '联系方式' },
]

onMounted(fetchContent)
</script>

<template>
  <div class="content-editor">
    <div class="editor-header">
      <div>
        <p class="kicker">CMS</p>
        <h2>内容管理</h2>
      </div>
    </div>

    <nav class="section-tabs">
      <button
        v-for="s in sections"
        :key="s.key"
        type="button"
        class="section-tab"
        :class="{ active: activeSection === s.key }"
        @click="activeSection = s.key"
      >{{ s.label }}</button>
    </nav>

    <!-- 站点基本信息 -->
    <div class="editor-section" v-show="activeSection === 'site'">
      <div class="section-head">
        <h3>站点基本信息</h3>
      </div>
      <div class="field-grid two-col">
        <label>
          <span>标题前缀</span>
          <input v-model="form.site.titlePrefix" type="text" placeholder="Hi, I'm" />
        </label>
        <label>
          <span>名字 / 标题</span>
          <input v-model="form.site.title" type="text" placeholder="Your Name" />
        </label>
        <label>
          <span>副标题前缀</span>
          <input v-model="form.site.subtitlePrefix" type="text" placeholder="A" />
        </label>
        <label>
          <span>副标题名称</span>
          <input v-model="form.site.subtitleName" type="text" placeholder="Developer" />
        </label>
        <label class="full">
          <span>像素文字</span>
          <input v-model="form.site.pixelText" type="text" placeholder="像素艺术标语" />
        </label>
      </div>
    </div>

    <!-- 个人简介 -->
    <div class="editor-section" v-show="activeSection === 'intro'">
      <div class="section-head">
        <h3>个人简介</h3>
      </div>
      <div class="field-grid one-col">
        <label>
          <span>标语 / Headline</span>
          <input v-model="form.intro.headline" type="text" placeholder="用一句话介绍自己" />
        </label>
        <label>
          <span>简介正文</span>
          <textarea v-model="form.intro.summary" rows="5" placeholder="详细介绍..."></textarea>
        </label>
      </div>
    </div>

    <!-- 技能列表 -->
    <div class="editor-section" v-show="activeSection === 'skills'">
      <div class="section-head">
        <h3>技能列表</h3>
        <p class="section-hint">每行一个技能，顺序即展示顺序</p>
      </div>
      <div class="field-grid one-col">
        <label>
          <span>技能（每行一条）</span>
          <textarea
            :value="skillsText"
            @input="skillsText = $event.target.value"
            rows="10"
            placeholder="Vue.js&#10;TypeScript&#10;Node.js"
          ></textarea>
        </label>
      </div>
      <div class="skills-preview" v-if="form.skills.length">
        <p class="preview-label">预览</p>
        <div class="chips-wrap">
          <span
            v-for="(skill, i) in form.skills"
            :key="i"
            class="skill-chip"
            :style="{ '--chip-color': `var(${CHIP_COLORS[i % CHIP_COLORS.length]})` }"
          >{{ skill }}</span>
        </div>
      </div>
    </div>

    <!-- 项目列表 -->
    <div class="editor-section" v-show="activeSection === 'projects'">
      <div class="section-head">
        <h3>项目列表</h3>
      </div>

      <div class="project-list">
        <div
          v-for="(proj, i) in projectForms"
          :key="i"
          class="project-card"
        >
          <div class="project-card-head">
            <strong class="proj-index">项目 {{ i + 1 }}</strong>
            <button type="button" class="delete-proj-btn" @click="removeProject(i)">删除项目</button>
          </div>
          <div class="field-grid two-col">
            <label>
              <span>项目名称</span>
              <input v-model="proj.name" type="text" placeholder="My Project" />
            </label>
            <label>
              <span>演示链接</span>
              <input v-model="proj.url" type="text" placeholder="https://..." />
            </label>
            <label>
              <span>GitHub</span>
              <input v-model="proj.github" type="text" placeholder="https://github.com/..." />
            </label>
            <label>
              <span>标签（逗号分隔）</span>
              <input v-model="proj.tags" type="text" placeholder="Vue, TypeScript, Node" />
            </label>
            <label class="full">
              <span>项目描述</span>
              <textarea v-model="proj.description" rows="3" placeholder="项目简介..."></textarea>
            </label>
          </div>
        </div>

        <div class="empty-projects" v-if="!projectForms.length">
          暂无项目，点击下方添加
        </div>
      </div>

      <button type="button" class="add-project-btn" @click="addProject">＋ 添加项目</button>
    </div>

    <!-- 联系方式 -->
    <div class="editor-section" v-show="activeSection === 'contact'">
      <div class="section-head">
        <h3>联系方式</h3>
      </div>
      <div class="field-grid one-col">
        <label>
          <span>邮箱</span>
          <input v-model="form.contact.email" type="email" placeholder="you@example.com" />
        </label>
        <label>
          <span>微信号</span>
          <input v-model="form.contact.wechat" type="text" placeholder="微信 ID" />
        </label>
        <label>
          <span>GitHub</span>
          <input v-model="form.contact.github" type="text" placeholder="https://github.com/..." />
        </label>
      </div>
    </div>

    <!-- Save bar -->
    <div class="save-bar">
      <button type="button" class="save-btn" :disabled="saving" @click="saveContent">
        {{ saving ? '保存中...' : '保存内容' }}
      </button>
    </div>

    <!-- Toast -->
    <Transition name="toast">
      <div
        v-if="toast.msg"
        class="toast"
        :class="toast.type"
      >{{ toast.msg }}</div>
    </Transition>
  </div>
</template>

<style scoped>
.content-editor {
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: relative;
}

.editor-header h2 {
  font-size: 1.1rem;
  color: var(--dark);
}

/* Section tabs */
.section-tabs {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--line);
  padding-bottom: 0;
}

.section-tab {
  padding: 8px 16px;
  border-radius: 8px 8px 0 0;
  border: 1px solid transparent;
  border-bottom: none;
  background: transparent;
  color: var(--soft);
  font-size: .85rem;
  cursor: pointer;
  transition: .15s;
  margin-bottom: -1px;
}

.section-tab:hover { color: var(--dark); background: var(--bg1); }

.section-tab.active {
  background: var(--panel);
  border-color: var(--line);
  color: var(--dark);
  font-weight: 600;
}

/* Sections */
.editor-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: var(--bg1);
  border: 1px solid var(--line);
  border-radius: 0 12px 12px 12px;
  padding: 22px;
}

.editor-section .section-head h3 {
  font-size: .95rem;
  color: var(--dark);
  margin-bottom: 2px;
}

.section-hint {
  font-size: .78rem;
  color: var(--soft);
}

/* Field grid */
.field-grid {
  display: grid;
  gap: 14px;
}

.field-grid.two-col { grid-template-columns: 1fr 1fr; }
.field-grid.one-col { grid-template-columns: 1fr; }

.field-grid label {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field-grid label.full { grid-column: 1 / -1; }

.field-grid label > span {
  font-size: .78rem;
  color: var(--soft);
  font-weight: 600;
  letter-spacing: .02em;
}

.field-grid input,
.field-grid textarea,
.field-grid select {
  padding: 8px 11px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  color: var(--dark);
  font-size: .875rem;
  transition: border-color .15s;
  resize: vertical;
}

.field-grid input:focus,
.field-grid textarea:focus {
  outline: none;
  border-color: var(--c4);
}

/* Skills preview */
.skills-preview {
  padding-top: 4px;
}

.preview-label {
  font-size: .76rem;
  color: var(--soft);
  font-weight: 600;
  letter-spacing: .06em;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.chips-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.skill-chip {
  display: inline-block;
  padding: 5px 14px;
  border-radius: 999px;
  font-size: .82rem;
  font-weight: 600;
  color: var(--chip-color, var(--c1));
  background: color-mix(in srgb, var(--chip-color, var(--c1)) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--chip-color, var(--c1)) 30%, transparent);
}

/* Projects */
.project-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.project-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.project-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.proj-index {
  font-size: .85rem;
  color: var(--soft);
}

.delete-proj-btn {
  padding: 4px 12px;
  border-radius: 6px;
  border: 1px solid var(--line);
  background: transparent;
  color: var(--soft);
  font-size: .78rem;
  cursor: pointer;
  transition: .15s;
}

.delete-proj-btn:hover {
  border-color: var(--c1);
  color: var(--c1);
}

.empty-projects {
  padding: 24px;
  text-align: center;
  color: var(--soft);
  font-size: .88rem;
  border: 1px dashed var(--line);
  border-radius: 10px;
}

.add-project-btn {
  align-self: flex-start;
  padding: 8px 18px;
  border-radius: 8px;
  border: 1px dashed var(--c4);
  background: color-mix(in srgb, var(--c4) 8%, transparent);
  color: var(--c4);
  font-size: .85rem;
  font-weight: 600;
  cursor: pointer;
  transition: .15s;
}

.add-project-btn:hover {
  background: color-mix(in srgb, var(--c4) 14%, transparent);
}

/* Save bar */
.save-bar {
  display: flex;
  justify-content: flex-end;
  padding-top: 4px;
}

.save-btn {
  padding: 10px 28px;
  background: linear-gradient(135deg, var(--c4), var(--c5));
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: .9rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity .15s;
}

.save-btn:disabled { opacity: .6; cursor: not-allowed; }
.save-btn:not(:disabled):hover { opacity: .88; }

/* Toast */
.toast {
  position: fixed;
  bottom: 28px;
  right: 28px;
  padding: 12px 20px;
  border-radius: 10px;
  font-size: .875rem;
  font-weight: 600;
  box-shadow: 0 8px 24px rgba(0,0,0,.12);
  z-index: 1000;
  pointer-events: none;
}

.toast.success {
  background: var(--c3);
  color: #fff;
}

.toast.error {
  background: var(--c1);
  color: #fff;
}

.toast-enter-active,
.toast-leave-active { transition: opacity .2s, transform .2s; }
.toast-enter-from,
.toast-leave-to { opacity: 0; transform: translateY(8px); }

@media (max-width: 600px) {
  .field-grid.two-col { grid-template-columns: 1fr; }
  .section-tabs { gap: 2px; }
  .section-tab { padding: 7px 11px; font-size: .8rem; }
}
</style>
