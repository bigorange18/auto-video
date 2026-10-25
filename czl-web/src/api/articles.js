async function requestJson(url) {
  const response = await fetch(url)
  const payload = await response.json()
  if (!response.ok || !payload.success) {
    throw new Error(payload.message || '文章请求失败')
  }
  return payload.data
}

export async function fetchAllArticles(pageSize = 50) {
  const safePageSize = Math.min(50, Math.max(1, Number(pageSize) || 50))
  const articles = []
  let page = 1
  let totalPages = 1

  do {
    const data = await requestJson(
      `/api/public/articles?page=${page}&pageSize=${safePageSize}`,
    )
    articles.push(...(data.articles || []))
    totalPages = Math.max(1, Number(data.totalPages) || 1)
    page += 1
  } while (page <= totalPages)

  return articles
}
