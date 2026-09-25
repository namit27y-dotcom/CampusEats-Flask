const rawApiUrl = (import.meta.env.VITE_API_URL as string | undefined)?.trim();

const defaultBaseUrl = (rawApiUrl && rawApiUrl !== 'undefined')
  ? rawApiUrl.replace(/\/+$/, '')
  : '/api';

const candidateUrls: string[] = Array.from(
  new Set(
    [
      defaultBaseUrl,
      '/api',
    ].filter(Boolean) as string[]
  )
);

let activeBaseUrl = defaultBaseUrl;

export const getApiBaseUrl = () => activeBaseUrl;

export const apiRequest = async (
  endpoint: string,
  options: RequestInit = {}
) => {
  const token = localStorage.getItem('token');
  const headers = new Headers(options.headers);

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Ensure leading slash
  let cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;

  // Prioritize activeBaseUrl, followed by other candidate URLs if network fails
  const urlsToTry = Array.from(new Set([
    activeBaseUrl,
    ...candidateUrls,
  ])).filter(Boolean);

  let response: Response | null = null;
  let lastNetworkError: any = null;

  for (const baseUrl of urlsToTry) {
    // If endpoint already starts with /api and baseUrl is /api, avoid /api/api
    let fullUrl = '';
    if (baseUrl === '/api' && cleanEndpoint.startsWith('/api/')) {
      fullUrl = cleanEndpoint;
    } else {
      fullUrl = `${baseUrl}${cleanEndpoint}`;
    }
    try {
      const res = await fetch(fullUrl, {
        ...options,
        headers,
      });

      // If static hosting (Vercel/Netlify SPA) returns 405 Method Not Allowed for POST/PUT on static route
      if (res.status === 405) {
        continue;
      }

      // If static hosting returns HTML page (index.html SPA fallback) instead of JSON API response
      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('text/html')) {
        continue;
      }

      response = res;
      activeBaseUrl = baseUrl;
      lastNetworkError = null;
      break;
    } catch (err: any) {
      lastNetworkError = err;
      // Connection/Network error, continue to next candidate
    }
  }

  if (!response) {
    throw new Error(
      `Unable to reach backend server. ${lastNetworkError?.message || 'Please check backend server connection.'}`
    );
  }

  const text = await response.text();
  let data: any = {};
  if (text && text.trim()) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { message: text };
    }
  }

  if (!response.ok) {
    const errorMsg =
      data.message ||
      data.error ||
      `Request failed with status ${response.status} (${response.statusText})`;
    const error: any = new Error(errorMsg);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
};

