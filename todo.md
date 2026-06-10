# OneShot TODO

## 出版商 Handler

| 出版商 | 域名 | 是否需要 CF | 方法 | 状态 |
|--------|------|------------|------|------|
| ACM | `dl.acm.org` | ✅ | CF proxy `/doi/pdf/{doi}` | ✅ |
| IEEE | `ieeexplore.ieee.org` | ❌ | `/stampPDF/getPDF.jsp?arnumber={id}` | ✅ |
| Springer | `link.springer.com` | ✅ | CF proxy `/content/pdf/{doi}.pdf` | ✅ |
| Dagstuhl | `drops.dagstuhl.de` | ❌ | scrape page html for pdf link | ✅ |
| Nature | `www.nature.com` | ❌ | `/articles/{id}.pdf` | ✅ |
| SIAM | `epubs.siam.org` | ✅ | CF proxy `/doi/pdf/{doi}?download=true` | ✅ |
| Sage | `journals.sagepub.com` | ✅ | tokenized, needs headless | ❌ |
| IOP | `iopscience.iop.org` | ✅ | reCAPTCHA → auto_open_doi | ❌ |
### 测试用 DOI / 链接

- **Springer**: `10.1007/978-3-540-68552-4_24` ✅
- **Dagstuhl**: `10.4230/LIPIcs.CPM.2021.15` ✅
- **Nature**: `10.1038/s41467-018-04978-z` ✅
- **SIAM**: `10.1137/0136016` ✅

**Difficult:**

- **Sage**: `10.1068/b306` — tokenized, needs headless browser
- **IOP**: `10.1088/1755-1315/526/1/012190` — reCAPTCHA redirect, use `auto_open_doi_on_fail`

## 长期目标

- [ ] CF bypass server 支持 headed 模式 + captcha 检测，弹出浏览器窗口让用户手动验证后自动继续下载
- [ ] Sage headless browser handler
- [ ] `{journal}` 占位符支持
- [ ] 状态浮窗透明背景
- [ ] 批量下载 / 全部下载按钮
