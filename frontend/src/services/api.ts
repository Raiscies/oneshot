/**
 * OneShot API 服务
 * 
 * 连接后端 FastAPI 服务 (oneshot/api.py)
 */

const API_BASE = 'http://localhost:8000'

export interface Paper {
  title: string
  authors: string[]
  year?: number
  abstract?: string
  ccf_rank?: string
  doi?: string
  citation_number?: number
  citations?: number
}

export interface SearchResponse {
  papers: Paper[]
  captured_text: string
}

export async function searchPapers(query: string, capturedText: string = ''): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE}/api/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      captured_text: capturedText,
    }),
  })
  
  if (!response.ok) {
    throw new Error(`搜索失败: ${response.statusText}`)
  }
  
  return response.json()
}

export async function getResult(): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE}/api/result`)
  
  if (!response.ok) {
    throw new Error(`获取结果失败: ${response.statusText}`)
  }
  
  return response.json()
}
