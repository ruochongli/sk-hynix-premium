# 7709.HK / SK 海力士 实时溢价查询网页

一个用于查看 **南方东英 SK 海力士每日杠杆(2x)产品（7709.HK）** 相对估算 NAV 实时溢价的小工具。

## 数据来源

- **7709.HK 实时价格**：Yahoo Finance
- **SK 海力士实时价格**：Yahoo Finance（`000660.KS`）
- **官方最新 NAV**：南方东英官网 API（`CSOP SK Hynix Daily (2x) Leveraged Product`）

## 溢价计算方式

1. 取 SK 海力士上一交易日收盘价到当前价的涨幅 `r`。
2. 按 2x 杠杆估算当前 NAV：
   - `估算 HKD NAV = 官方 HKD NAV × (1 + 2 × r)`
   - `估算 USD NAV = 官方 USD NAV × (1 + 2 × r)`
3. 实时溢价：
   - `溢价 = (7709.HK 现价 − 估算 HKD NAV) / 估算 HKD NAV × 100%`

> 该估算未计入管理费、 swap/期权成本、汇率波动等细节，仅供快速参考，不构成投资建议。

---

## 方案 A：本地运行（功能最全，实时）

### Windows

双击 `start.bat`，或在本目录下打开 PowerShell/CMD：

```powershell
.venv\Scripts\python app.py
```

### macOS / Linux

```bash
./start.sh
```

打开浏览器访问：

```
http://localhost:5000
```

---

## 方案 B：部署到 GitHub Pages（免费在线网页）

GitHub Pages 只能托管**静态网页**，无法直接跑 Flask 后端。因此这里把前端放在 `docs/`，再通过 **Cloudflare Worker** 做数据代理。

### 1. 部署 Cloudflare Worker 代理

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com)。
2. 进入 **Workers & Pages** → **Create application** → **Create Worker**。
3. 把 `worker.js` 的内容粘贴进去，保存。
4. 得到一个地址，例如：

```
https://sk-hynix-premium-proxy.your-subdomain.workers.dev
```

### 2. 修改静态页面里的代理地址

打开 `docs/index.html`，把这一行换成你的 Worker 地址：

```js
const PROXY_URL = "https://sk-hynix-premium-proxy.your-subdomain.workers.dev";
```

### 3. 上传到 GitHub 并开启 Pages

1. 在 GitHub 新建一个仓库，例如 `sk-hynix-premium`。
2. 把本项目 push 上去：

```bash
git init
git add .
git commit -m "init"
git branch -M main
git remote add origin https://github.com/你的用户名/sk-hynix-premium.git
git push -u origin main
```

3. 进入仓库 **Settings → Pages**：
   - **Source**：Deploy from a branch
   - **Branch**：main
   - **Folder**：/docs
   - 点击 **Save**

4. 等待 1-2 分钟后，即可访问：

```
https://你的用户名.github.io/sk-hynix-premium
```

---

## 目录结构

```
.
├── app.py              # Flask 后端（本地运行）
├── templates/
│   └── index.html      # Flask 版本前端
├── docs/
│   ├── index.html      # GitHub Pages 静态版本
│   └── .nojekyll
├── worker.js           # Cloudflare Worker CORS 代理
├── start.bat           # Windows 本地启动
├── start.sh            # macOS/Linux 本地启动
├── requirements.txt
└── README.md
```

---

## 免责声明

本工具仅用于技术学习与数据展示，数据来自公开接口，可能存在延迟或错误，不构成任何投资建议。
