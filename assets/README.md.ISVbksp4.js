import{_ as a,o as i,c as n,a2 as e}from"./chunks/framework.BsCfuO2w.js";const c=JSON.parse('{"title":"nova-server 文档","description":"","frontmatter":{},"headers":[],"relativePath":"README.md","filePath":"README.md","lastUpdated":1782142938000}'),p={name:"README.md"};function l(t,s,h,d,r,k){return i(),n("div",null,[...s[0]||(s[0]=[e(`<h1 id="nova-server-文档" tabindex="-1">nova-server 文档 <a class="header-anchor" href="#nova-server-文档" aria-label="Permalink to &quot;nova-server 文档&quot;">​</a></h1><p>本目录是用 <strong>VitePress</strong> 构建的 nova-server 文档站点源码。</p><h2 id="本地预览" tabindex="-1">本地预览 <a class="header-anchor" href="#本地预览" aria-label="Permalink to &quot;本地预览&quot;">​</a></h2><div class="language-bash vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">bash</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># 安装依赖（首次）</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">npm</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> install</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># 启动开发服务器（热重载）</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">npm</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> run</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> docs:dev</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># → http://localhost:5173</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># 构建静态站点</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">npm</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> run</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> docs:build</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># → 输出到 docs/.vitepress/dist/</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># 预览构建结果</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">npm</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> run</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> docs:preview</span></span></code></pre></div><h2 id="目录结构" tabindex="-1">目录结构 <a class="header-anchor" href="#目录结构" aria-label="Permalink to &quot;目录结构&quot;">​</a></h2><div class="language- vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang"></span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>docs/</span></span>
<span class="line"><span>├── .vitepress/</span></span>
<span class="line"><span>│   └── config.mjs          ← VitePress 配置（导航、侧栏、主题）</span></span>
<span class="line"><span>├── index.md                ← 首页（产品介绍 + 特性矩阵）</span></span>
<span class="line"><span>│</span></span>
<span class="line"><span>├── guide/                  ← 用户指南</span></span>
<span class="line"><span>│   ├── what-is-nova-server.md</span></span>
<span class="line"><span>│   ├── getting-started.md</span></span>
<span class="line"><span>│   ├── deploy-to-esp32.md</span></span>
<span class="line"><span>│   ├── routing.md</span></span>
<span class="line"><span>│   ├── request-response.md</span></span>
<span class="line"><span>│   ├── async-streaming.md</span></span>
<span class="line"><span>│   └── hooks-and-errors.md</span></span>
<span class="line"><span>│</span></span>
<span class="line"><span>├── examples/               ← 示例代码详解</span></span>
<span class="line"><span>│   ├── 01-hello.md</span></span>
<span class="line"><span>│   ├── 02-sensors.md</span></span>
<span class="line"><span>│   ├── 03-static-files.md</span></span>
<span class="line"><span>│   └── 04-streaming.md</span></span>
<span class="line"><span>│</span></span>
<span class="line"><span>├── hardware/               ← ESP32 硬件注意事项</span></span>
<span class="line"><span>│   ├── gpio-safety.md</span></span>
<span class="line"><span>│   ├── wifi.md</span></span>
<span class="line"><span>│   ├── memory.md</span></span>
<span class="line"><span>│   └── power-and-reset.md</span></span>
<span class="line"><span>│</span></span>
<span class="line"><span>└── api/                    ← API 参考</span></span>
<span class="line"><span>    ├── nova-server.md</span></span>
<span class="line"><span>    ├── request.md</span></span>
<span class="line"><span>    ├── response.md</span></span>
<span class="line"><span>    ├── url-pattern.md</span></span>
<span class="line"><span>    └── utilities.md</span></span></code></pre></div><h2 id="写作约定" tabindex="-1">写作约定 <a class="header-anchor" href="#写作约定" aria-label="Permalink to &quot;写作约定&quot;">​</a></h2><h3 id="_1-vitepress-容器语法" tabindex="-1">1. VitePress 容器语法 <a class="header-anchor" href="#_1-vitepress-容器语法" aria-label="Permalink to &quot;1. VitePress 容器语法&quot;">​</a></h3><div class="language-markdown vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">markdown</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">::: tip 小贴士</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">这是提示内容</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:::</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">::: warning 警告</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">这是警告内容</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:::</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">::: danger 危险</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">不要这样做！</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:::</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">::: details 点击展开</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">详细内容</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:::</span></span></code></pre></div><h3 id="_2-代码块标注语言" tabindex="-1">2. 代码块标注语言 <a class="header-anchor" href="#_2-代码块标注语言" aria-label="Permalink to &quot;2. 代码块标注语言&quot;">​</a></h3><div class="language-python vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">python</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Python / MicroPython 代码</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">print</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">(</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;hello&#39;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">)</span></span></code></pre></div><div class="language-bash vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">bash</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Shell 命令</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">mpremote</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> connect</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> COM3</span></span></code></pre></div><h3 id="_3-内部链接" tabindex="-1">3. 内部链接 <a class="header-anchor" href="#_3-内部链接" aria-label="Permalink to &quot;3. 内部链接&quot;">​</a></h3><p>用绝对路径（不带 <code>.md</code>）：</p><div class="language-markdown vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">markdown</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">看 [</span><span style="--shiki-light:#032F62;--shiki-light-text-decoration:underline;--shiki-dark:#DBEDFF;--shiki-dark-text-decoration:underline;">路由</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">](</span><span style="--shiki-light:#24292E;--shiki-light-text-decoration:underline;--shiki-dark:#E1E4E8;--shiki-dark-text-decoration:underline;">/guide/routing</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">)</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">看 [</span><span style="--shiki-light:#032F62;--shiki-light-text-decoration:underline;--shiki-dark:#DBEDFF;--shiki-dark-text-decoration:underline;">NovaServer API</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">](</span><span style="--shiki-light:#24292E;--shiki-light-text-decoration:underline;--shiki-dark:#E1E4E8;--shiki-dark-text-decoration:underline;">/api/nova-server</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">)</span></span></code></pre></div><h3 id="_4-平台说明" tabindex="-1">4. 平台说明 <a class="header-anchor" href="#_4-平台说明" aria-label="Permalink to &quot;4. 平台说明&quot;">​</a></h3><p>文档面向 <strong>ESP32 / NovaMP</strong>。如果代码在 PC 上也能跑，可加注：</p><div class="language-markdown vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">markdown</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">&gt; PC 上也能跑（仅用于测试）</span></span></code></pre></div><h2 id="部署" tabindex="-1">部署 <a class="header-anchor" href="#部署" aria-label="Permalink to &quot;部署&quot;">​</a></h2><p>构建产物 <code>docs/.vitepress/dist/</code> 是纯静态文件，可以部署到任何静态托管：</p><ul><li>GitHub Pages</li><li>Vercel</li><li>Netlify</li><li>Cloudflare Pages</li><li>nginx / Apache</li></ul><h3 id="github-pages-示例" tabindex="-1">GitHub Pages 示例 <a class="header-anchor" href="#github-pages-示例" aria-label="Permalink to &quot;GitHub Pages 示例&quot;">​</a></h3><div class="language-bash vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">bash</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># 构建</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">npm</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> run</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> docs:build</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># 推送到 gh-pages 分支</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">git</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> add</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> docs/.vitepress/dist</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">git</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> commit</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -m</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;docs: build&quot;</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">git</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> subtree</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> push</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> --prefix</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> docs/.vitepress/dist</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> origin</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> gh-pages</span></span></code></pre></div><h2 id="添加新页面" tabindex="-1">添加新页面 <a class="header-anchor" href="#添加新页面" aria-label="Permalink to &quot;添加新页面&quot;">​</a></h2><ol><li>在对应分类目录下创建 <code>.md</code> 文件</li><li>在 <code>docs/.vitepress/config.mjs</code> 的 <code>sidebar</code> 里加导航</li><li>用相对路径互相链接</li></ol><h2 id="已知问题" tabindex="-1">已知问题 <a class="header-anchor" href="#已知问题" aria-label="Permalink to &quot;已知问题&quot;">​</a></h2><ul><li>❌ 不要用 <code>::: warning 标题</code> 这种带标题的语法 — VitePress 默认只支持不带标题的容器</li><li>✅ 用 <code>::: warning\\n标题\\n内容\\n:::</code> 这种格式</li></ul>`,27)])])}const g=a(p,[["render",l]]);export{c as __pageData,g as default};
