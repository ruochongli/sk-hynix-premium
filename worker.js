/**
 * Cloudflare Worker：CORS 代理
 * 给 GitHub Pages 上的静态页面提供实时数据转发能力。
 *
 * 部署步骤：
 * 1. 登录 https://dash.cloudflare.com，进入 Workers & Pages。
 * 2. 创建一个新的 Worker，把这个文件内容贴进去。
 * 3. 保存后得到一个地址，例如 https://sk-hynix-premium-proxy.your-subdomain.workers.dev
 * 4. 把 docs/index.html 里的 PROXY_URL 改成这个地址。
 */

const USER_AGENT =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36";

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const target = url.searchParams.get("url");

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    if (!target) {
      return new Response("Missing ?url= parameter", { status: 400, headers: corsHeaders() });
    }

    const init = {
      method: request.method,
      headers: {
        "User-Agent": USER_AGENT,
      },
    };

    if (request.method === "POST") {
      const contentType = request.headers.get("content-type");
      if (contentType) {
        init.headers["Content-Type"] = contentType;
      }
      init.body = request.body;
    }

    try {
      const resp = await fetch(target, init);
      const body = await resp.arrayBuffer();
      const headers = {
        ...corsHeaders(),
        "Content-Type": resp.headers.get("content-type") || "application/json",
      };
      return new Response(body, { status: resp.status, headers });
    } catch (err) {
      return new Response(`Proxy error: ${err.message}`, { status: 502, headers: corsHeaders() });
    }
  },
};
