import assert from 'node:assert/strict'
import test from 'node:test'
import { filterPublicTasks, mergeTask } from './store.js'

const tasks = [
  {
    id: 'task_public',
    externalId: 'dev-task-public',
    title: 'Public task',
    projectSlug: 'personal-site',
    visibility: 'public',
    status: 'in_progress',
    priority: 'high',
    notes: 'Private notes must not leak',
    tags: ['api'],
  },
  {
    id: 'task_private',
    title: 'Private task',
    projectSlug: 'personal-site',
    visibility: 'private',
    status: 'todo',
  },
]

test('public task filtering excludes private tasks and notes', () => {
  const result = filterPublicTasks(tasks, { projectSlug: 'personal-site' })

  assert.equal(result.length, 1)
  assert.equal(result[0].id, 'task_public')
  assert.equal('notes' in result[0], false)
  assert.equal('visibility' in result[0], false)
  assert.equal('externalId' in result[0], false)
})

test('public task filtering supports project and status', () => {
  assert.equal(filterPublicTasks(tasks, { status: 'todo' }).length, 0)
  assert.equal(filterPublicTasks(tasks, { projectSlug: 'another-project' }).length, 0)
  assert.equal(filterPublicTasks(tasks, { status: 'in_progress' }).length, 1)
})

test('partial task updates preserve omitted fields', () => {
  const existing = {
    id: 'task_existing',
    externalId: 'external-1',
    title: 'Original',
    projectSlug: 'personal-site',
    visibility: 'public',
    status: 'in_progress',
    priority: 'high',
    dueDate: '2026-12-01',
    tags: ['review'],
    notes: 'keep-note',
    createdAt: '2026-10-01T00:00:00.000Z',
  }
  const updated = mergeTask(
    existing,
    { title: 'Updated' },
    '2026-10-25T00:00:00.000Z',
  )

  assert.equal(updated.title, 'Updated')
  assert.equal(updated.projectSlug, 'personal-site')
  assert.equal(updated.visibility, 'public')
  assert.equal(updated.status, 'in_progress')
  assert.equal(updated.dueDate, '2026-12-01')
  assert.deepEqual(updated.tags, ['review'])
  assert.equal(updated.notes, 'keep-note')
})
