export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(`/api${path}`, { ...options, headers })
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const message = body?.error?.message || (response.status === 422 ? '输入内容不符合要求，请检查后重试。' : '请求失败，请确认本地服务仍在运行。')
    throw new Error(message)
  }
  return body as T
}
export const requestId = () => crypto.randomUUID()
