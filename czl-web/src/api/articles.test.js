import assert from 'node:assert/strict'
import test from 'node:test'
import { fetchAllArticles } from './articles.js'

test('fetchAllArticles loads every page', async () => {
  const originalFetch = globalThis.fetch
  const requestedPages = []

  globalThis.fetch = async (url) => {
    const page = Number(new URL(url, 'http://localhost').searchParams.get('page'))
    requestedPages.push(page)
    return {
      ok: true,
      async json() {
        return {
          success: true,
          data: {
            articles: [{ id: `article-${page}` }],
            totalPages: 3,
          },
        }
      },
    }
  }

  try {
    const articles = await fetchAllArticles(1)
    assert.deepEqual(requestedPages, [1, 2, 3])
    assert.deepEqual(articles.map((article) => article.id), [
      'article-1',
      'article-2',
      'article-3',
    ])
  } finally {
    globalThis.fetch = originalFetch
  }
})
