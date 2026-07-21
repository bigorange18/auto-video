<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { renderMarkdown } from '../../markdown.js'

// ── State ─────────────────────────────────────────────────────────────────────
const articles = ref([])
const loading = ref(true)
const view = ref('list') // 'list' | 'editor'

// ── MD File Upload ────────────────────────────────────────────────────────────
const uploadInput = ref(null)
const uploading = ref(false)
const uploadNotice = ref('')

async function onUploadChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  if (!file.name.endsWith('.md')) {
    uploadNotice.value = '只支持 .md 文件'
    return
  }
  uploading.value = true
  uploadNotice.value = ''
  try {
    const text = await file.text()
    const res = await fetch(`/api/admin/articles/upload?filename=${encodeURIComponent(file.name)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain' },
      body: text,
    })
    const json = await res.json()
    if (json.success) {
      uploadNotice.value = `✓ ${file.name} 上传成功`
      await fetchArticles()
    } else {
      uploadNotice.value = `✗ ${json.message || '上传失败'}`
    }
  } catch (err) {
    uploadNotice.value = `✗ 上传出错`
  } finally {
    uploading.value = false
    e.target.value = ''
    setTimeout(() => { uploadNotice.value = '' }, 4000)
  }
}

// ── Inline delete confirm ─────────────────────────────────────────────────────
const pendingDelete = ref(null)

// ── Cover image upload ────────────────────────────────────────────────────────
const coverUploading = ref(false)

async function onCoverImageUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  coverUploading.value = true
  try {
    const res = await fetch(`/api/admin/upload/image?filename=${encodeURIComponent(file.name)}`, {
      method: 'POST',
      headers: { 'Content-Type': file.type || 'image/jpeg' },
      body: file,
    })
    const json = await res.json()
    if (json.success) {
      form.coverImage = json.url
    } else {
      alert(json.message || '上传失败')
    }
  } catch {
    alert('上传出错')
  } finally {
    coverUploading.value = false
    e.target.value = ''
  }
}

// ── Editor state ──────────────────────────────────────────────────────────────
const editId = ref(null)
const saving = ref(false)
const dirty = ref(false)

const form = reactive({
  title: '',
  type: 'blog',
  content: '',
  summary: '',
  coverImage: '',
  tags: '',
  published: true,
})

// Track dirty state
watch(form, () => { dirty.value = true }, { deep: true })

// ── Live preview ──────────────────────────────────────────────────────────────
const preview = computed(() => renderMarkdown(form.content))

// ── Fetch ─────────────────────────────────────────────────────────────────────
async function fetchArticles() {
  loading.value = true
  try {
    const res = await fetch('/api/admin/articles')
    const json = await res.json()
    if (json.success) articles.value = json.data
  } finally {
    loading.value = false
  }
}

onMounted(fetchArticles)

// ── Helpers ───────────────────────────────────────────────────────────────────
function wordCount(content) {
  if (!content) return 0
  return content.replace(/\s+/g, '').length
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

function coverGradient(id) {
  const colors = [
    'linear-gradient(135deg,#f97316,#ec4899)',
    'linear-gradient(135deg,#3b82f6,#8b5cf6)',
    'linear-gradient(135deg,#10b981,#14b8a6)',
    'linear-gradient(135deg,#f59e0b,#ef4444)',
    'linear-gradient(135deg,#8b5cf6,#ec4899)',
  ]
  // derive a stable index from id
  const n = typeof id === 'number' ? id : (String(id).charCodeAt(0) || 0)
  return colors[n % colors.length]
}

// ── List view actions ─────────────────────────────────────────────────────────
function openCreate() {
  Object.assign(form, {
    title: '', type: 'blog', content: '',
    summary: '', coverImage: '', tags: '', published: true,
  })
  editId.value = null
  dirty.value = false
  view.value = 'editor'
}

function openEdit(article) {
  Object.assign(form, {
    title: article.title || '',
    type: article.type || 'blog',
    content: article.content || '',
    summary: article.summary || '',
    coverImage: article.coverImage || '',
    tags: (article.tags || []).join(', '),
    published: !!article.published,
  })
  editId.value = article.id
  dirty.value = false
  view.value = 'editor'
}

function backToList() {
  view.value = 'list'
  editId.value = null
}

async function togglePublished(article) {
  const res = await fetch(`/api/admin/articles/${article.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...article, published: !article.published }),
  })
  const json = await res.json()
  if (json.success) await fetchArticles()
}

function askDelete(id) { pendingDelete.value = id }
function cancelDelete() { pendingDelete.value = null }
async function confirmDelete(id) {
  await fetch(`/api/admin/articles/${id}`, { method: 'DELETE' })
  pendingDelete.value = null
  await fetchArticles()
}

// ── Save ──────────────────────────────────────────────────────────────────────
async function saveArticle() {
  if (!form.title.trim()) return
  saving.value = true
  try {
    const payload = {
      title: form.title.trim(),
      type: form.type,
      content: form.content,
      summary: form.summary.trim(),
      coverImage: form.coverImage.trim(),
      tags: form.tags.split(',').map((t) => t.trim()).filter(Boolean),
      published: form.published,
    }
    let res
    if (editId.value) {
      res = await fetch(`/api/admin/articles/${editId.value}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    } else {
      res = await fetch('/api/admin/articles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    }
    const json = await res.json()
    if (json.success) {
      dirty.value = false
      await fetchArticles()
      if (!editId.value && json.data?.id) {
        editId.value = json.data.id
      }
    }
  } finally {
    saving.value = false
  }
}

// ── Markdown toolbar ──────────────────────────────────────────────────────────
const textarea = ref(null)

function insertSyntax(before, after = '') {
  const el = textarea.value
  if (!el) return
  const start = el.selectionStart
  const end = el.selectionEnd
  const selected = form.content.slice(start, end)
  const insert = before + selected + after
  form.content = form.content.slice(0, start) + insert + form.content.slice(end)
  // restore cursor
  const newPos = start + before.length + selected.length + after.length
  setTimeout(() => {
    el.focus()
    el.setSelectionRange(
      selected ? start + before.length : newPos,
      selected ? start + before.length + selected.length : newPos,
    )
  })
}

const toolbarItems = [
  { label: 'B', title: '粗体', before: '**', after: '**' },
  { label: 'I', title: '斜体', before: '*', after: '*' },
  { label: 'H1', title: '一级标题', before: '# ', after: '' },
  { label: 'H2', title: '二级标题', before: '## ', after: '' },
  { label: '`', title: '行内代码', before: '`', after: '`' },
  { label: '```', title: '代码块', before: '```\n', after: '\n```' },
  { label: '链接', title: '链接', before: '[', after: '](url)' },
  { label: '图片', title: '图片', before: '![', after: '](url)' },
  { label: '分割线', title: '分割线', before: '\n---\n', after: '' },
  { label: '• 列表', title: '无序列表', before: '- ', after: '' },
  { label: '1. 列表', title: '有序列表', before: '1. ', after: '' },
]
</script>

<template>
  <div class="aa-root">

    <!-- ════════════════ LIST VIEW ════════════════ -->
    <template v-if="view === 'list'">
      <div class="aa-toolbar">
        <h3 class="aa-toolbar-title">文章列表</h3>
        <div class="aa-toolbar-actions">
          <span v-if="uploadNotice" class="aa-upload-notice">{{ uploadNotice }}</span>
          <label class="aa-upload-btn" :class="{ disabled: uploading }">
            <input
              ref="uploadInput"
              type="file"
              accept=".md"
              style="display:none"
              @change="onUploadChange"
            />
            {{ uploading ? '上传中…' : '⬆ 上传 MD' }}
          </label>
          <button type="button" class="aa-new-btn" @click="openCreate">＋ 新建文章</button>
        </div>
      </div>

      <div v-if="loading" class="aa-empty">加载中…</div>

      <div v-else-if="articles.length === 0" class="aa-empty">
        <div class="aa-empty-icon">📝</div>
        <p>暂无文章，点击新建吧</p>
      </div>

      <div v-else class="aa-table-wrap">
        <table class="aa-table">
          <thead>
            <tr>
              <th>封面</th>
              <th>标题</th>
              <th>类型</th>
              <th>状态</th>
              <th>字数</th>
              <th>创建日期</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="article in articles" :key="article.id">
              <!-- Cover thumbnail -->
              <td class="aa-col-cover">
                <img
                  v-if="article.coverImage"
                  :src="article.coverImage"
                  class="aa-thumb"
                  :alt="article.title"
                />
                <div
                  v-else
                  class="aa-thumb-fallback"
                  :style="{ background: coverGradient(article.id) }"
                ></div>
              </td>

              <!-- Title -->
              <td class="aa-col-title">
                <span class="aa-article-title">{{ article.title }}</span>
              </td>

              <!-- Type badge -->
              <td class="aa-col-type">
                <span class="aa-type-badge">{{ article.type || '博客' }}</span>
              </td>

              <!-- Published toggle -->
              <td class="aa-col-status">
                <button
                  type="button"
                  class="aa-pub-toggle"
                  :class="{ published: article.published }"
                  @click="togglePublished(article)"
                >{{ article.published ? '已发布' : '未发布' }}</button>
              </td>

              <!-- Word count -->
              <td class="aa-col-words">
                <span class="aa-muted">{{ wordCount(article.content) }} 字</span>
              </td>

              <!-- Date -->
              <td class="aa-col-date">
                <span class="aa-muted">{{ formatDate(article.createdAt) }}</span>
              </td>

              <!-- Actions -->
              <td class="aa-col-actions">
                <button type="button" class="aa-edit-btn" @click="openEdit(article)">编辑</button>

                <template v-if="pendingDelete === article.id">
                  <span class="aa-del-text">确认删除？</span>
                  <button type="button" class="aa-del-yes" @click="confirmDelete(article.id)">确认</button>
                  <button type="button" class="aa-del-no" @click="cancelDelete">取消</button>
                </template>
                <button
                  v-else
                  type="button"
                  class="aa-del-btn"
                  @click="askDelete(article.id)"
                >删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- ════════════════ EDITOR VIEW ════════════════ -->
    <template v-else>
      <!-- Top bar -->
      <div class="aa-editor-topbar">
        <button type="button" class="aa-back-btn" @click="backToList">← 返回列表</button>
        <div class="aa-editor-controls">
          <input
            v-model="form.title"
            type="text"
            class="aa-title-input"
            placeholder="文章标题…"
          />
          <select v-model="form.type" class="aa-type-select">
            <option value="blog">博客</option>
            <option value="life">生活</option>
            <option value="photo">摄影</option>
          </select>
          <label class="aa-pub-label">
            <input v-model="form.published" type="checkbox" class="aa-pub-checkbox" />
            <span>发布</span>
          </label>
          <span v-if="dirty" class="aa-dirty-dot" title="有未保存的修改">●</span>
          <button
            type="button"
            class="aa-save-btn"
            :disabled="saving"
            @click="saveArticle"
          >{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>

      <!-- Two-column editor -->
      <div class="aa-editor-body">
        <!-- Left: toolbar + textarea -->
        <div class="aa-editor-left">
          <div class="aa-md-toolbar">
            <button
              v-for="item in toolbarItems"
              :key="item.label"
              type="button"
              class="aa-md-btn"
              :title="item.title"
              @click="insertSyntax(item.before, item.after)"
            >{{ item.label }}</button>
          </div>
          <textarea
            ref="textarea"
            v-model="form.content"
            class="aa-md-textarea"
            rows="20"
            placeholder="在此输入 Markdown 内容…"
            spellcheck="false"
          ></textarea>
        </div>

        <!-- Right: live preview -->
        <div class="aa-editor-right">
          <div class="aa-preview-label">预览</div>
          <div class="aa-preview prose" v-html="preview"></div>
        </div>
      </div>

      <!-- Below editor: meta fields -->
      <div class="aa-meta-row">
        <div class="aa-meta-field">
          <label class="aa-label">摘要</label>
          <textarea
            v-model="form.summary"
            class="aa-input"
            rows="3"
            placeholder="文章摘要…"
          ></textarea>
        </div>
        <div class="aa-meta-field">
          <label class="aa-label">封面图</label>
          <div class="cover-input-row">
            <input
              v-model="form.coverImage"
              type="text"
              class="aa-input"
              placeholder="https:// 或点击上传本地图片"
            />
            <label class="cover-upload-btn" :class="{ disabled: coverUploading }">
              <input type="file" accept="image/*" style="display:none" @change="onCoverImageUpload" />
              {{ coverUploading ? '上传中…' : '📷 上传' }}
            </label>
          </div>
          <div v-if="form.coverImage" class="cover-preview">
            <img :src="form.coverImage" alt="封面预览" />
            <button type="button" class="cover-remove" @click="form.coverImage = ''">✕</button>
          </div>
        </div>
        <div class="aa-meta-field">
          <label class="aa-label">标签（逗号分隔）</label>
          <input
            v-model="form.tags"
            type="text"
            class="aa-input"
            placeholder="Vue, 前端, JavaScript"
          />
        </div>
      </div>
    </template>

  </div>
</template>

<style scoped>
/* ── Root ── */
.aa-root { display: flex; flex-direction: column; gap: 16px; }

/* ── Toolbar ── */
.aa-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.aa-toolbar-title { font-size: 1rem; font-weight: 700; color: var(--dark); }
.aa-toolbar-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.aa-upload-btn {
  display: inline-flex; align-items: center; cursor: pointer;
  padding: 7px 14px; border-radius: 8px; font-size: 0.82rem; font-weight: 600;
  background: var(--bg2, #f0f4fb); color: var(--dark, #333);
  border: 1px solid var(--line, #ddd);
  transition: background 0.15s, border-color 0.15s;
}
.aa-upload-btn:hover { background: var(--c5, #6366f1); color: #fff; border-color: transparent; }
.aa-upload-btn.disabled { opacity: 0.6; pointer-events: none; }
.aa-upload-notice { font-size: 0.78rem; color: var(--c2, #22c55e); }

/* cover image upload */
.cover-input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.cover-input-row .aa-input { flex: 1; }
.cover-upload-btn {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  padding: 7px 14px;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 600;
  background: var(--bg2, #f0f4fb);
  color: var(--dark, #333);
  border: 1px solid var(--line, #ddd);
  white-space: nowrap;
  transition: background 0.15s;
}
.cover-upload-btn:hover { background: var(--c5, #6366f1); color: #fff; border-color: transparent; }
.cover-upload-btn.disabled { opacity: 0.6; pointer-events: none; }
.cover-preview {
  position: relative;
  margin-top: 8px;
  display: inline-block;
}
.cover-preview img {
  display: block;
  max-height: 140px;
  max-width: 100%;
  border-radius: 8px;
  border: 1px solid var(--line, #eee);
  object-fit: cover;
}
.cover-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  background: rgba(0,0,0,0.55);
  color: #fff;
  border: none;
  border-radius: 50%;
  width: 22px;
  height: 22px;
  font-size: 0.7rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.aa-new-btn {
  padding: 8px 20px; border-radius: 999px; border: none;
  background: linear-gradient(135deg, var(--c8), var(--c6));
  color: #fff; font-size: .88rem; font-weight: 600; cursor: pointer; transition: .2s;
}
.aa-new-btn:hover { opacity: .88; transform: translateY(-1px); }

/* ── Empty ── */
.aa-empty {
  display: flex; flex-direction: column; align-items: center;
  gap: 10px; padding: 48px 20px; color: var(--soft); text-align: center;
}
.aa-empty-icon { font-size: 2.4rem; opacity: .7; }

/* ── Table ── */
.aa-table-wrap { overflow-x: auto; }
.aa-table {
  width: 100%; border-collapse: collapse; font-size: .88rem;
}
.aa-table th {
  padding: 10px 12px; text-align: left; color: var(--soft);
  font-size: .78rem; font-weight: 600; text-transform: uppercase; letter-spacing: .06em;
  border-bottom: 2px solid var(--line);
}
.aa-table td { padding: 12px 12px; border-bottom: 1px solid var(--line); vertical-align: middle; }
.aa-table tr:last-child td { border-bottom: none; }
.aa-table tr:hover td { background: rgba(0,0,0,.015); }

.aa-col-cover { width: 56px; }
.aa-thumb { width: 40px; height: 40px; border-radius: 8px; object-fit: cover; display: block; }
.aa-thumb-fallback {
  width: 40px; height: 40px; border-radius: 8px; display: block; flex-shrink: 0;
}

.aa-col-title { max-width: 240px; }
.aa-article-title {
  font-weight: 600; color: var(--dark);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}

.aa-type-badge {
  padding: 2px 10px; border-radius: 999px; font-size: .74rem; font-weight: 600;
  background: rgba(59,130,246,.1); color: var(--c4);
}

.aa-pub-toggle {
  padding: 3px 12px; border-radius: 999px; font-size: .78rem; font-weight: 600;
  border: 1px solid transparent; cursor: pointer; transition: .2s;
  background: rgba(148,163,184,.1); color: #64748b;
}
.aa-pub-toggle.published {
  background: rgba(34,197,94,.12); color: #16a34a; border-color: rgba(34,197,94,.2);
}
.aa-pub-toggle:hover { opacity: .8; }

.aa-muted { color: var(--soft); font-size: .84rem; }

.aa-col-actions { white-space: nowrap; }
.aa-edit-btn {
  padding: 4px 12px; border-radius: 8px; border: 1px solid var(--line);
  background: transparent; color: var(--soft); font-size: .8rem; cursor: pointer; transition: .2s;
  margin-right: 4px;
}
.aa-edit-btn:hover { border-color: var(--c4); color: var(--c4); }
.aa-del-btn {
  padding: 4px 12px; border-radius: 8px; border: 1px solid transparent;
  background: transparent; color: var(--soft); font-size: .8rem; cursor: pointer; transition: .2s;
}
.aa-del-btn:hover { background: rgba(239,68,68,.08); color: #ef4444; border-color: rgba(239,68,68,.2); }
.aa-del-text { font-size: .78rem; color: #ef4444; margin-right: 4px; }
.aa-del-yes {
  padding: 4px 10px; border-radius: 8px; border: none;
  background: #ef4444; color: #fff; font-size: .8rem; cursor: pointer;
  margin-right: 4px; transition: .2s;
}
.aa-del-yes:hover { background: #dc2626; }
.aa-del-no {
  padding: 4px 10px; border-radius: 8px; border: 1px solid var(--line);
  background: transparent; color: var(--soft); font-size: .8rem; cursor: pointer;
}

/* ── Editor top bar ── */
.aa-editor-topbar {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  padding-bottom: 14px; border-bottom: 1px solid var(--line);
}
.aa-back-btn {
  padding: 7px 16px; border-radius: 999px; border: 1px solid var(--line);
  background: transparent; color: var(--soft); font-size: .86rem;
  cursor: pointer; transition: .2s; white-space: nowrap;
}
.aa-back-btn:hover { border-color: var(--c4); color: var(--c4); }

.aa-editor-controls {
  display: flex; align-items: center; gap: 10px; flex: 1; flex-wrap: wrap;
}
.aa-title-input {
  flex: 1; min-width: 200px; padding: 8px 14px;
  border: 1px solid var(--line); border-radius: 10px;
  background: var(--bg1); font-size: 1rem; font-weight: 600; color: var(--dark);
  outline: none; transition: .2s;
}
.aa-title-input:focus { border-color: var(--c5); box-shadow: 0 0 0 3px rgba(139,92,246,.08); }

.aa-type-select {
  padding: 8px 12px; border: 1px solid var(--line); border-radius: 10px;
  background: var(--bg1); font-size: .88rem; color: var(--dark); cursor: pointer;
  outline: none; transition: .2s;
}

.aa-pub-label {
  display: flex; align-items: center; gap: 5px;
  font-size: .86rem; color: var(--soft); cursor: pointer; white-space: nowrap;
}
.aa-pub-checkbox { cursor: pointer; }

.aa-dirty-dot { color: #f97316; font-size: 1rem; line-height: 1; }

.aa-save-btn {
  padding: 8px 22px; border-radius: 999px; border: none;
  background: linear-gradient(135deg, var(--c4), var(--c5));
  color: #fff; font-size: .88rem; font-weight: 600; cursor: pointer; transition: .2s;
  white-space: nowrap;
}
.aa-save-btn:hover:not(:disabled) { opacity: .88; }
.aa-save-btn:disabled { opacity: .5; cursor: not-allowed; }

/* ── Two-column editor ── */
.aa-editor-body {
  display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start;
}
@media (max-width: 800px) {
  .aa-editor-body { grid-template-columns: 1fr; }
}

.aa-editor-left { display: flex; flex-direction: column; gap: 0; }
.aa-editor-right { display: flex; flex-direction: column; gap: 8px; }

/* ── Markdown toolbar ── */
.aa-md-toolbar {
  display: flex; flex-wrap: wrap; gap: 4px; padding: 8px;
  background: var(--bg2); border: 1px solid var(--line);
  border-bottom: none; border-radius: 10px 10px 0 0;
}
.aa-md-btn {
  padding: 4px 10px; border-radius: 6px; border: 1px solid var(--line);
  background: var(--panel); color: var(--dark); font-size: .8rem;
  cursor: pointer; transition: .15s; white-space: nowrap;
}
.aa-md-btn:hover { background: var(--bg1); border-color: var(--c5); color: var(--c5); }

/* ── Textarea ── */
.aa-md-textarea {
  width: 100%; padding: 12px 14px;
  border: 1px solid var(--line); border-radius: 0 0 10px 10px;
  background: var(--bg1); font-size: .88rem; font-family: 'Fira Code', 'Consolas', monospace;
  color: var(--dark); resize: vertical; outline: none; line-height: 1.7;
  min-height: 360px; transition: border-color .2s;
}
.aa-md-textarea:focus { border-color: var(--c5); box-shadow: 0 0 0 3px rgba(139,92,246,.08); }

/* ── Preview ── */
.aa-preview-label {
  font-size: .76rem; font-weight: 600; letter-spacing: .08em;
  text-transform: uppercase; color: var(--soft); padding: 0 2px;
}
.aa-preview {
  padding: 16px 20px;
  background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
  min-height: 360px; overflow-y: auto;
  font-size: .9rem; line-height: 1.75; color: var(--dark);
}

/* prose styles inside preview */
.aa-preview :deep(h1),
.aa-preview :deep(h2),
.aa-preview :deep(h3) { font-weight: 700; margin: 1em 0 .4em; color: var(--dark); }
.aa-preview :deep(h1) { font-size: 1.4rem; }
.aa-preview :deep(h2) { font-size: 1.2rem; }
.aa-preview :deep(h3) { font-size: 1.05rem; }
.aa-preview :deep(p) { margin: .6em 0; }
.aa-preview :deep(a) { color: var(--c4); text-decoration: underline; }
.aa-preview :deep(ul),
.aa-preview :deep(ol) { padding-left: 1.4em; margin: .5em 0; }
.aa-preview :deep(li) { margin: .2em 0; }
.aa-preview :deep(code) {
  font-family: 'Fira Code', monospace; font-size: .85em;
  background: var(--bg2); padding: 1px 5px; border-radius: 4px;
}
.aa-preview :deep(pre) {
  background: #1e1e2e; color: #cdd6f4; border-radius: 10px;
  padding: 14px 16px; overflow-x: auto; font-size: .84em; margin: .8em 0;
}
.aa-preview :deep(pre code) { background: transparent; padding: 0; }
.aa-preview :deep(blockquote) {
  border-left: 3px solid var(--c5); padding-left: 12px;
  color: var(--soft); margin: .6em 0;
}
.aa-preview :deep(hr) { border: none; border-top: 1px solid var(--line); margin: 1em 0; }
.aa-preview :deep(img) { max-width: 100%; border-radius: 8px; }
.aa-preview :deep(table) { width: 100%; border-collapse: collapse; margin: .6em 0; }
.aa-preview :deep(th),
.aa-preview :deep(td) { padding: 6px 10px; border: 1px solid var(--line); font-size: .88em; }
.aa-preview :deep(th) { background: var(--bg2); font-weight: 600; }

/* ── Meta row below editor ── */
.aa-meta-row {
  display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px;
  padding-top: 16px; border-top: 1px solid var(--line);
}
@media (max-width: 800px) {
  .aa-meta-row { grid-template-columns: 1fr; }
}

.aa-meta-field { display: flex; flex-direction: column; gap: 5px; }
.aa-label { font-size: .82rem; color: var(--soft); font-weight: 500; }
.aa-input {
  padding: 8px 12px; border: 1px solid var(--line); border-radius: 10px;
  background: var(--bg1); font-size: .88rem; color: var(--dark);
  outline: none; resize: vertical; transition: .2s;
}
.aa-input:focus { border-color: var(--c5); box-shadow: 0 0 0 3px rgba(139,92,246,.08); }
</style>
