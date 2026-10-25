import assert from 'node:assert/strict'
import test from 'node:test'
import { normalizeProject, normalizeProjects } from './projectSchema.js'

test('normalizes legacy project fields', () => {
  const project = normalizeProject({
    title: 'Legacy Project',
    desc: 'Legacy description',
    link: 'https://example.com/demo',
    github: 'https://github.com/example/project',
    tech: ['Vue', 'Node', 'Vue'],
  })

  assert.equal(project.name, 'Legacy Project')
  assert.equal(project.category, 'other')
  assert.equal(project.summary, 'Legacy description')
  assert.equal(project.stack.length, 2)
  assert.equal(project.demoUrl, 'https://example.com/demo')
  assert.equal(project.repoUrl, 'https://github.com/example/project')
})

test('keeps supported project categories', () => {
  assert.equal(normalizeProject({ name: 'AI Tool', category: 'ai' }).category, 'ai')
  assert.equal(normalizeProject({ name: 'Unknown', category: 'invalid' }).category, 'other')
})

test('rejects unsafe project links', () => {
  const project = normalizeProject({
    name: 'Unsafe',
    demoUrl: 'javascript:alert(1)',
    repoUrl: 'data:text/html,test',
  })

  assert.equal(project.demoUrl, '')
  assert.equal(project.repoUrl, '')
})

test('assigns stable fallback slugs', () => {
  const projects = normalizeProjects([{ name: '中文项目' }, { name: 'Another Project' }])

  assert.equal(projects[0].slug, 'project-1')
  assert.equal(projects[1].slug, 'another-project')
})
