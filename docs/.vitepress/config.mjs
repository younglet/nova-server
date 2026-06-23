import { defineConfig } from 'vitepress'

// GitHub Pages project site uses /<repo>/ subpath; keep '/' for local dev.
const base = process.env.GITHUB_ACTIONS ? '/nova-server/' : '/'

export default defineConfig({
  base,
  title: 'nova-server',
  description: 'MicroPython 异步 Web 框架 · 专为 NovaMP 2.0 / ESP32 设计',
  lang: 'zh-CN',
  lastUpdated: true,
  cleanUrls: true,
  ignoreDeadLinks: true,

  head: [
    ['meta', { name: 'theme-color', content: '#3eaf7c' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:title', content: 'nova-server' }],
    ['meta', { property: 'og:description', content: 'ESP32 MicroPython 异步 Web 框架' }],
  ],

  themeConfig: {
    siteTitle: 'nova-server',

    nav: [
      {
        text: '🌟 生态',
        items: [
          { text: 'NovaMP 固件', link: 'https://code.stemstar.com/novamp' },
          { text: 'nova-frontend', link: 'https://github.com/' },
          { text: 'nova-server (当前)', link: '/guide/what-is-nova-server' },
          { text: 'nova-chart', link: 'https://younglet.github.io/nova-chart/' },
          { text: 'Nova Animation Format (.naf)', link: 'https://github.com/' },
        ],
      },
      { text: '指南', link: '/guide/getting-started', activeMatch: '/guide/' },
      { text: '示例', link: '/examples/01-hello', activeMatch: '/examples/' },
      { text: '硬件', link: '/hardware/gpio-safety', activeMatch: '/hardware/' },
      { text: 'API', link: '/api/nova-server', activeMatch: '/api/' },
    ],

    sidebar: {
      '/guide/': [
        {
          text: '入门',
          items: [
            { text: '介绍', link: '/guide/what-is-nova-server' },
            { text: '必读基础', link: '/guide/basics' },
            { text: '快速开始', link: '/guide/getting-started' },
            { text: '部署到 ESP32', link: '/guide/deploy-to-esp32' },
          ],
        },
        {
          text: '上手（必看）',
          items: [
            { text: '你的第一个 GET', link: '/guide/first-route' },
            { text: '加更多路由', link: '/guide/more-routes' },
            { text: 'URL 参数', link: '/guide/url-parameters' },
            { text: '查询字符串', link: '/guide/query-strings' },
            { text: '返回 JSON', link: '/guide/return-json' },
          ],
        },
        {
          text: '收数据与报错',
          items: [
            { text: 'POST 请求', link: '/guide/post-requests' },
            { text: '错误处理', link: '/guide/errors' },
          ],
        },
        {
          text: '进阶',
          items: [
            { text: 'Request 对象', link: '/guide/request-object' },
            { text: 'Response 对象', link: '/guide/response-object' },
            { text: '钩子', link: '/guide/hooks' },
            { text: '静态文件', link: '/guide/static-files' },
            { text: '实时推送', link: '/guide/async-streaming' },
          ],
        },
      ],
      '/examples/': [
        { text: '01 — Hello World', link: '/examples/01-hello' },
        { text: '02 — 传感器 API', link: '/examples/02-sensors' },
        { text: '03 — 静态文件服务', link: '/examples/03-static-files' },
        { text: '04 — 流式响应', link: '/examples/04-streaming' },
      ],
      '/hardware/': [
        { text: 'GPIO 安全', link: '/hardware/gpio-safety' },
        { text: 'WiFi 最佳实践', link: '/hardware/wifi' },
        { text: '内存监控', link: '/hardware/memory' },
        { text: '功耗与重启', link: '/hardware/power-and-reset' },
      ],
      '/api/': [
        { text: 'NovaServer', link: '/api/nova-server' },
        { text: 'Request', link: '/api/request' },
        { text: 'Response', link: '/api/response' },
        { text: 'URLPattern', link: '/api/url-pattern' },
        { text: '工具函数', link: '/api/utilities' },
      ],
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/' },
    ],

    footer: {
      message: '专为 NovaMP 2.0 设计 · powered by stemstar',
      copyright: '',
    },

    search: {
      provider: 'local',
    },

    outline: {
      level: [2, 3],
      label: '本页目录',
    },

    docFooter: {
      prev: '上一篇',
      next: '下一篇',
    },
  },

  // VitePress 原生支持 ::: warning / ::: tip / ::: danger / ::: info / ::: details 容器
  // 用法：
  //   ::: warning 标题
  //   内容
  //   :::
  markdown: {
    theme: {
      light: 'github-light',
      dark: 'github-dark',
    },
    lineNumbers: false,
  },
})