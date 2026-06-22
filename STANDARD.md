# nova-frontend 项目规范

> 所有 nova-frontend 生态下的项目都应遵循的规范。
> 这份文档是事实标准，每个项目都按此执行。

---

## 1. 品牌标注

### 1.1 Footer 文本

所有项目的文档站点底部统一显示：

```
专为 NovaMP 2.0 设计 · powered by stemstar
```

#### VitePress（推荐）

`docs/.vitepress/config.mjs`：

```js
export default defineConfig({
  themeConfig: {
    footer: {
      message: '专为 NovaMP 2.0 设计 · powered by stemstar',
      copyright: '',    // 留空，不要第二行
    },
  },
})
```

#### README.md

每个项目 `README.md` 末尾：

```markdown
## 📜 License

powered by stemstar
```

### 1.2 不写什么

- ❌ 不要写 MIT / Apache / GPL — 这是 stemstar 内部项目
- ❌ 不要写 `© 项目名` 或 `Copyright 2024 ...`
- ❌ 不要写多行花哨的版权说明（"由 XX 公司出品，受 XX 协议保护..."）
- ✅ 只写 `专为 NovaMP 2.0 设计 · powered by stemstar`，干净一行

---

## 2. NovaMP 版本

所有项目统一写 **NovaMP 2.0**（带版本号）。即使固件版本会升级，文档里也固定写 2.0。

- ✅ `NovaMP 2.0` 固件
- ✅ `专为 NovaMP 2.0 设计`
- ❌ `NovaMP` （太短，不像产品）
- ❌ `NovaMP v2.0.1` （跟具体版本绑死）

NovaMP 的实际下载页面：`https://code.stemstar.com/novamp`

---

## 3. 导航生态链接

每个项目的 VitePress 顶部 nav 第一个位置是 **🌟 生态** 下拉菜单，里面是相关项目链接。

### 3.1 标准格式

```js
nav: [
  {
    text: '🌟 生态',
    items: [
      { text: 'NovaMP 固件', link: 'https://code.stemstar.com/novamp' },
      { text: 'nova-frontend', link: '<nova-frontend 主仓库 URL>' },
      { text: '<当前项目名> (当前)', link: '<当前项目文档首页>' },
      // 其他相关项目...
    ],
  },
  { text: '指南', link: '/<...>' },
  { text: '示例', link: '/<...>' },
  // 其他 nav 项...
]
```

### 3.2 当前生态项目清单

| 项目 | 链接 | 文档站 |
|------|------|--------|
| NovaMP 固件 | https://code.stemstar.com/novamp | （外部） |
| nova-frontend | https://github.com/ | （外部） |
| nova-server | https://github.com/ | `/guide/what-is-nova-server` |
| nova-chart | https://github.com/ | （外部） |
| Nova Animation Format (.naf) | https://github.com/ | （外部） |

新项目加入时，**所有现有项目的生态菜单都要同步加一行**。

---

## 4. 项目命名

| 类型 | 约定 | 例子 |
|------|------|------|
| 项目名 | 全小写，连字符分隔 | `nova-server`、`nova-chart` |
| 文件名 | 同项目名 + `.py` | `nova_server.py` |
| 类名 | 大驼峰 | `NovaServer`、`URLPattern` |
| 函数/变量 | 小写 + 下划线 | `connect_wifi`、`is_safe` |
| URL 路径 | 全小写 | `/api/state`、`/static/` |

---

## 5. 文档首页（hero）

每个项目首页至少有：

```yaml
hero:
  name: <项目名>
  text: <一句话定位>
  tagline: <关键卖点，用 · 分隔，3-4 个>
  actions:
    - theme: brand
      text: <第一个 CTA>
      link: <第一个行动>
```

例子（nova-server）：

```yaml
hero:
  name: nova-server
  text: ESP32 上的微型 Web 框架
  tagline: 单文件 35 KB · 内置于 NovaMP 2.0 · 不用懂 Web 也能用
  actions:
    - theme: brand
      text: 5 分钟跑起来
      link: /guide/basics
```

---

## 6. 禁用清单

文档里**禁止**出现：

- ❌ `curl` 命令（测试相关，文档不需要）
- ❌ `mpremote` 详细教程（只在部署页里出现）
- ❌ `pytest` / `TESTING.md` 引用（测试和文档分离）
- ❌ 真实的 WiFi 名称和密码（用 `你的WiFi名` / `你的WiFi密码` 占位）
- ❌ 真实的 IP 地址（用 `192.168.x.x` 占位）
- ❌ MIT / Apache / GPL 协议字眼
- ❌ 临时占位（`todo`、`fixme`、`xxx`）

---

## 7. 检查清单

新建项目或改文档时对照检查：

- [ ] Footer 是 `专为 NovaMP 2.0 设计 · powered by stemstar`
- [ ] README.md 末尾 `powered by stemstar`
- [ ] 第一个 nav 是 `🌟 生态` 下拉，里面有所有相关项目链接
- [ ] "NovaMP" 写作 "NovaMP 2.0"（带版本号）
- [ ] 没有 curl / pytest / 真实 WiFi 名字
- [ ] 文档用中文（除非用户面向英文用户）
- [ ] 首页 hero 有 name + text + tagline + 至少 1 个 button

---

## 8. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2024-XX-XX | 初版（nova-server 实施） |