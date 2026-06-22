# nova-server 文档

本目录是用 **VitePress** 构建的 nova-server 文档站点源码。

## 本地预览

```bash
# 安装依赖（首次）
npm install

# 启动开发服务器（热重载）
npm run docs:dev
# → http://localhost:5173

# 构建静态站点
npm run docs:build
# → 输出到 docs/.vitepress/dist/

# 预览构建结果
npm run docs:preview
```

## 目录结构

```
docs/
├── .vitepress/
│   └── config.mjs          ← VitePress 配置（导航、侧栏、主题）
├── index.md                ← 首页（产品介绍 + 特性矩阵）
│
├── guide/                  ← 用户指南
│   ├── what-is-nova-server.md
│   ├── getting-started.md
│   ├── deploy-to-esp32.md
│   ├── routing.md
│   ├── request-response.md
│   ├── async-streaming.md
│   └── hooks-and-errors.md
│
├── examples/               ← 示例代码详解
│   ├── 01-hello.md
│   ├── 02-sensors.md
│   ├── 03-static-files.md
│   └── 04-streaming.md
│
├── hardware/               ← ESP32 硬件注意事项
│   ├── gpio-safety.md
│   ├── wifi.md
│   ├── memory.md
│   └── power-and-reset.md
│
└── api/                    ← API 参考
    ├── nova-server.md
    ├── request.md
    ├── response.md
    ├── url-pattern.md
    └── utilities.md
```

## 写作约定

### 1. VitePress 容器语法

```markdown
::: tip 小贴士
这是提示内容
:::

::: warning 警告
这是警告内容
:::

::: danger 危险
不要这样做！
:::

::: details 点击展开
详细内容
:::
```

### 2. 代码块标注语言

```python
# Python / MicroPython 代码
print('hello')
```

```bash
# Shell 命令
mpremote connect COM3
```

### 3. 内部链接

用绝对路径（不带 `.md`）：

```markdown
看 [路由](/guide/routing)
看 [NovaServer API](/api/nova-server)
```

### 4. 平台说明

文档面向 **ESP32 / NovaMP**。如果代码在 PC 上也能跑，可加注：

```markdown
> PC 上也能跑（仅用于测试）
```

## 部署

构建产物 `docs/.vitepress/dist/` 是纯静态文件，可以部署到任何静态托管：

- GitHub Pages
- Vercel
- Netlify
- Cloudflare Pages
- nginx / Apache

### GitHub Pages 示例

```bash
# 构建
npm run docs:build

# 推送到 gh-pages 分支
git add docs/.vitepress/dist
git commit -m "docs: build"
git subtree push --prefix docs/.vitepress/dist origin gh-pages
```

## 添加新页面

1. 在对应分类目录下创建 `.md` 文件
2. 在 `docs/.vitepress/config.mjs` 的 `sidebar` 里加导航
3. 用相对路径互相链接

## 已知问题

- ❌ 不要用 `::: warning 标题` 这种带标题的语法 — VitePress 默认只支持不带标题的容器
- ✅ 用 `::: warning\n标题\n内容\n:::` 这种格式