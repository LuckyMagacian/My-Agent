---
name: http-retry-handler
description: "处理 HTTP 请求因网络问题失败的代码实现指导。覆盖超时、断连、部分数据丢失、服务器错误等场景，提供重试策略、断点续传、错误恢复的标准化实现方案。当项目涉及 HTTP 请求、API 调用、文件下载、数据同步等网络操作时自动应用。"
---

# HTTP 请求失败处理规范

## 触发条件

| 条件 | 说明 |
| --- | --- |
| HTTP 请求代码 | 项目中存在 fetch、axios、requests 等 HTTP 调用 |
| 文件下载 | 大文件下载、批量下载场景 |
| API 集成 | 第三方 API 调用、微服务间通信 |
| 数据同步 | 离线同步、增量更新场景 |

---

## 代理配置

**固定代理地址**：`127.0.0.1:7890`

| 协议 | 地址格式 | 用途 |
| --- | --- | --- |
| HTTP | `http://127.0.0.1:7890` | HTTP/HTTPS 请求代理 |
| SOCKS5 | `socks5://127.0.0.1:7890` | TCP 流量代理 |

### 环境变量配置

```bash
# HTTP/HTTPS 代理
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890

# SOCKS5 代理 (部分工具支持)
export ALL_PROXY=socks5://127.0.0.1:7890

# 不走代理的地址
export NO_PROXY=localhost,127.0.0.1,::1
```

### TypeScript/Node.js 代理实现

```typescript
import { HttpsProxyAgent } from 'https-proxy-agent';
import { SocksProxyAgent } from 'socks-proxy-agent';

const PROXY_CONFIG = {
  http: 'http://127.0.0.1:7890',
  https: 'http://127.0.0.1:7890',
  socks5: 'socks5://127.0.0.1:7890'
};

// HTTP/HTTPS 代理
const httpsAgent = new HttpsProxyAgent(PROXY_CONFIG.http);

// SOCKS5 代理
const socksAgent = new SocksProxyAgent(PROXY_CONFIG.socks5);

// fetch 使用代理 (Node.js 18+)
async function fetchWithProxy(url: string, useSocks = false): Promise<Response> {
  const dispatcher = useSocks ? socksAgent : httpsAgent;

  return fetch(url, {
    // @ts-ignore - Node.js 特有选项
    dispatcher
  });
}
```

### Python 代理实现

```python
import httpx
import requests

PROXY_CONFIG = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890',
    'socks5': 'socks5://127.0.0.1:7890'
}

# requests 库
response = requests.get(url, proxies=PROXY_CONFIG)

# httpx 库
async with httpx.AsyncClient(proxy=PROXY_CONFIG['https']) as client:
    response = await client.get(url)

# SOCKS5 代理 (需安装 httpx[socks])
async with httpx.AsyncClient(proxy=PROXY_CONFIG['socks5']) as client:
    response = await client.get(url)
```

### Go 代理实现

```go
import (
    "net/http"
    "net/url"
    "golang.org/x/net/proxy"
)

// HTTP 代理
func httpClientWithProxy() *http.Client {
    proxyURL, _ := url.Parse("http://127.0.0.1:7890")
    return &http.Client{
        Transport: &http.Transport{
            Proxy: http.ProxyURL(proxyURL),
        },
    }
}

// SOCKS5 代理
func httpClientWithSocks5() *http.Client {
    dialer, _ := proxy.SOCKS5("tcp", "127.0.0.1:7890", nil, proxy.Direct)
    return &http.Client{
        Transport: &http.Transport{
            Dial: dialer.Dial,
        },
    }
}
```

---

## 一、错误分类与识别

### 1.1 网络层错误

| 错误类型 | 典型表现 | 可重试 | 优先级 |
| --- | --- | --- | --- |
| `ConnectionError` | 连接被拒绝、DNS 解析失败 | ✅ | 高 |
| `TimeoutError` | 连接超时、读取超时 | ✅ | 高 |
| `NetworkError` | 网络不可达、断网 | ✅ | 中 |
| `SSLError` | 证书验证失败 | ❌ | 低 |

### 1.2 HTTP 状态码分类

```typescript
enum RetryStrategy {
  NEVER = 'never',
  ALWAYS = 'always',
  CONDITIONAL = 'conditional'
}

const RETRY_CONFIG: Record<number, RetryStrategy> = {
  // 客户端错误 - 不重试
  400: RetryStrategy.NEVER,  // Bad Request
  401: RetryStrategy.NEVER,  // Unauthorized
  403: RetryStrategy.NEVER,  // Forbidden
  404: RetryStrategy.NEVER,  // Not Found
  422: RetryStrategy.NEVER,  // Unprocessable Entity

  // 服务器错误 - 可重试
  408: RetryStrategy.ALWAYS,  // Request Timeout
  429: RetryStrategy.ALWAYS,  // Too Many Requests
  500: RetryStrategy.CONDITIONAL,  // Internal Server Error
  502: RetryStrategy.ALWAYS,  // Bad Gateway
  503: RetryStrategy.ALWAYS,  // Service Unavailable
  504: RetryStrategy.ALWAYS,  // Gateway Timeout
};
```

### 1.3 部分数据失败识别

```typescript
interface PartialFailure {
  type: 'truncated_response' | 'incomplete_download' | 'chunk_missing';
  received: number;
  expected?: number;
  lastByte?: number;
}

function detectPartialFailure(response: Response, expectedSize?: number): PartialFailure | null {
  const contentLength = response.headers.get('content-length');
  const received = parseInt(contentLength || '0');

  if (expectedSize && received < expectedSize) {
    return {
      type: 'incomplete_download',
      received,
      expected: expectedSize,
      lastByte: received - 1
    };
  }

  if (response.body && !response.bodyUsed) {
    return { type: 'truncated_response', received: 0 };
  }

  return null;
}
```

---

## 二、重试策略实现

### 2.1 指数退避算法

```typescript
interface RetryConfig {
  maxRetries: number;         // 最大重试次数
  baseDelay: number;          // 基础延迟 (ms)
  maxDelay: number;           // 最大延迟 (ms)
  backoffFactor: number;      // 退避因子
  jitter: boolean;            // 是否添加随机抖动
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 30000,
  backoffFactor: 2,
  jitter: true
};

function calculateDelay(attempt: number, config: RetryConfig): number {
  const exponentialDelay = config.baseDelay * Math.pow(config.backoffFactor, attempt);
  const cappedDelay = Math.min(exponentialDelay, config.maxDelay);

  if (config.jitter) {
    // Full jitter: 0 ~ cappedDelay
    return Math.random() * cappedDelay;
  }

  return cappedDelay;
}

function getRetryAfterDelay(response: Response): number | null {
  const retryAfter = response.headers.get('retry-after');
  if (!retryAfter) return null;

  const seconds = parseInt(retryAfter);
  return isNaN(seconds) ? null : seconds * 1000;
}
```

### 2.2 重试执行器

```typescript
async function withRetry<T>(
  fn: () => Promise<T>,
  config: Partial<RetryConfig> = {},
  onRetry?: (error: Error, attempt: number) => void
): Promise<T> {
  const fullConfig = { ...DEFAULT_RETRY_CONFIG, ...config };
  let lastError: Error;

  for (let attempt = 0; attempt <= fullConfig.maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      if (!isRetryableError(error) || attempt === fullConfig.maxRetries) {
        throw error;
      }

      const delay = calculateDelay(attempt, fullConfig);
      onRetry?.(lastError, attempt + 1);

      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw lastError!;
}

function isRetryableError(error: unknown): boolean {
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return true; // Network error
  }

  if (error instanceof Response) {
    const strategy = RETRY_CONFIG[error.status];
    return strategy === RetryStrategy.ALWAYS ||
           (strategy === RetryStrategy.CONDITIONAL && error.status >= 500);
  }

  if (error instanceof DOMException && error.name === 'AbortError') {
    return true; // Timeout
  }

  return false;
}
```

---

## 三、断点续传实现

### 3.1 Range 请求

```typescript
interface ResumableDownload {
  url: string;
  downloaded: number;
  total?: number;
  etag?: string;
  lastModified?: string;
}

async function resumeDownload(
  state: ResumableDownload,
  onProgress?: (downloaded: number, total?: number) => void
): Promise<Blob> {
  const headers: HeadersInit = {};

  if (state.downloaded > 0) {
    headers['Range'] = `bytes=${state.downloaded}-`;
  }

  if (state.etag) {
    headers['If-Match'] = state.etag;
  } else if (state.lastModified) {
    headers['If-Unmodified-Since'] = state.lastModified;
  }

  const response = await fetch(state.url, { headers });

  // 检查是否支持断点续传
  if (response.status === 416) {
    // Range Not Satisfiable - 文件可能已完成或已变更
    throw new Error('Resume not supported or file changed');
  }

  if (response.status === 200) {
    // 服务器不支持 Range，返回完整内容
    state.downloaded = 0;
  }

  const total = parseInt(response.headers.get('content-length') || '0') + state.downloaded;
  const reader = response.body!.getReader();
  const chunks: Uint8Array[] = [];
  let downloaded = state.downloaded;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    chunks.push(value);
    downloaded += value.length;
    onProgress?.(downloaded, total);
  }

  return new Blob(chunks);
}
```

### 3.2 分块下载管理

```typescript
interface ChunkDownloader {
  url: string;
  chunkSize: number;
  totalSize: number;
  chunks: Map<number, Blob>;
  completedChunks: Set<number>;
}

async function downloadWithChunks(
  downloader: ChunkDownloader,
  concurrency: number = 3,
  onProgress?: (progress: number) => void
): Promise<Blob> {
  const totalChunks = Math.ceil(downloader.totalSize / downloader.chunkSize);
  const pendingChunks: number[] = [];

  for (let i = 0; i < totalChunks; i++) {
    if (!downloader.completedChunks.has(i)) {
      pendingChunks.push(i);
    }
  }

  const downloadChunk = async (chunkIndex: number): Promise<void> => {
    const start = chunkIndex * downloader.chunkSize;
    const end = Math.min(start + downloader.chunkSize - 1, downloader.totalSize - 1);

    const response = await fetch(downloader.url, {
      headers: { Range: `bytes=${start}-${end}` }
    });

    downloader.chunks.set(chunkIndex, await response.blob());
    downloader.completedChunks.add(chunkIndex);

    const progress = downloader.completedChunks.size / totalChunks;
    onProgress?.(progress);
  };

  // 并发下载
  const pool = new Array(Math.min(concurrency, pendingChunks.length)).fill(null);

  await Promise.all(
    pool.map(async () => {
      while (pendingChunks.length > 0) {
        const chunkIndex = pendingChunks.shift()!;
        await withRetry(() => downloadChunk(chunkIndex));
      }
    })
  );

  // 合并 chunks
  const sortedChunks = Array.from(downloader.chunks.entries())
    .sort(([a], [b]) => a - b)
    .map(([, blob]) => blob);

  return new Blob(sortedChunks);
}
```

---

## 四、超时控制

### 4.1 AbortController 封装

```typescript
interface TimeoutConfig {
  connect?: number;   // 连接超时
  read?: number;      // 读取超时
  total?: number;     // 总超时
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout: TimeoutConfig = {}
): Promise<Response> {
  const controller = new AbortController();
  const timeouts: NodeJS.Timeout[] = [];

  const cleanup = () => timeouts.forEach(clearTimeout);

  // 总超时
  if (timeout.total) {
    timeouts.push(
      setTimeout(() => controller.abort(), timeout.total)
    );
  }

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    cleanup();
    return response;
  } catch (error) {
    cleanup();
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error(`Request timeout after ${timeout.total}ms`);
    }
    throw error;
  }
}
```

### 4.2 流式响应超时

```typescript
async function* streamWithTimeout<T>(
  stream: ReadableStream<T>,
  chunkTimeout: number
): AsyncGenerator<T> {
  const reader = stream.getReader();

  try {
    while (true) {
      const result = await Promise.race([
        reader.read(),
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('Chunk timeout')), chunkTimeout)
        )
      ]);

      if (result.done) break;
      yield result.value;
    }
  } finally {
    reader.releaseLock();
  }
}
```

---

## 五、错误恢复模式

### 5.1 请求队列与重放

```typescript
interface QueuedRequest {
  id: string;
  request: Request;
  resolve: (value: Response) => void;
  reject: (reason: Error) => void;
  retries: number;
}

class RequestQueue {
  private queue: QueuedRequest[] = [];
  private processing = false;

  async enqueue(request: Request): Promise<Response> {
    return new Promise((resolve, reject) => {
      this.queue.push({
        id: crypto.randomUUID(),
        request: request.clone(),
        resolve,
        reject,
        retries: 0
      });

      if (!this.processing) {
        this.process();
      }
    });
  }

  private async process(): Promise<void> {
    this.processing = true;

    while (this.queue.length > 0) {
      const item = this.queue[0];

      try {
        const response = await fetch(item.request);
        item.resolve(response);
        this.queue.shift();
      } catch (error) {
        if (item.retries < 3 && isRetryableError(error)) {
          item.retries++;
          const delay = calculateDelay(item.retries, DEFAULT_RETRY_CONFIG);
          await new Promise(r => setTimeout(r, delay));
        } else {
          item.reject(error as Error);
          this.queue.shift();
        }
      }
    }

    this.processing = false;
  }
}
```

### 5.2 缓存降级

```typescript
interface CacheEntry<T> {
  data: T;
  timestamp: number;
  etag?: string;
}

class FallbackCache<T> {
  private cache = new Map<string, CacheEntry<T>>();
  private ttl: number;

  constructor(ttl: number = 5 * 60 * 1000) {
    this.ttl = ttl;
  }

  async fetchWithFallback(
    key: string,
    fetcher: () => Promise<T>,
    maxAge?: number
  ): Promise<T> {
    try {
      const data = await fetcher();
      this.cache.set(key, { data, timestamp: Date.now() });
      return data;
    } catch (error) {
      const cached = this.cache.get(key);
      const age = cached ? Date.now() - cached.timestamp : Infinity;

      if (cached && (!maxAge || age < maxAge)) {
        console.warn(`Using cached data for ${key} (${age}ms old)`);
        return cached.data;
      }

      throw error;
    }
  }

  get(key: string): T | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    if (Date.now() - entry.timestamp > this.ttl) {
      this.cache.delete(key);
      return null;
    }

    return entry.data;
  }
}
```

---

## 六、实现检查清单

在实现 HTTP 请求失败处理时，确认：

- [ ] **错误分类**：区分网络错误、HTTP 错误、超时错误
- [ ] **重试策略**：实现指数退避，避免重试风暴
- [ ] **超时控制**：设置合理的连接/读取/总超时
- [ ] **断点续传**：大文件下载支持 Range 请求
- [ ] **幂等性**：重试时保证请求幂等（POST 需特殊处理）
- [ ] **并发限制**：避免过多并发请求压垮服务器
- [ ] **错误上报**：记录失败请求用于监控和调试
- [ ] **降级方案**：网络不可用时的缓存降级策略

---

## 七、语言特定实现

### 7.1 Python (requests/httpx)

```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=30)
)
async def fetch_with_retry(url: str) -> httpx.Response:
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response
```

### 7.2 Go (net/http)

```go
func FetchWithRetry(url string, maxRetries int) (*http.Response, error) {
    client := &http.Client{Timeout: 30 * time.Second}

    for attempt := 0; attempt <= maxRetries; attempt++ {
        resp, err := client.Get(url)
        if err == nil && resp.StatusCode < 500 {
            return resp, nil
        }

        if attempt < maxRetries {
            delay := time.Duration(math.Pow(2, float64(attempt))) * time.Second
            time.Sleep(delay)
        }
    }

    return nil, errors.New("max retries exceeded")
}
```

---

## 与其他 Skill 的协作

- 与 `software-development-workflow` 配合：在网络相关功能开发时应用此规范
- 与 `attention-maintenance` 配合：在调试网络问题时保持对问题的追踪
