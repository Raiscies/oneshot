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
| APS | `journals.aps.org` | ✅ | CF proxy, replace /abstract/→/pdf/ | ✅ |
| Sage | `journals.sagepub.com` | ✅ | tokenized, needs headless | ❌ |
| IOP | `iopscience.iop.org` | ✅ | reCAPTCHA → auto_open_doi | ❌ |
### 测试用 DOI / 链接

- **Springer**: `10.1007/978-3-540-68552-4_24` ✅
    -> `https://link.springer.com/chapter/10.1007/978-3-540-68552-4_24`
    -> `https://link.springer.com/content/pdf/10.1007/978-3-540-68552-4.pdf`
- **Dagstuhl**: `10.4230/LIPIcs.CPM.2021.15` ✅
- **Nature**: `10.1038/s41467-018-04978-z` ✅
- **SIAM**: `10.1137/0136016` ✅
    -> `https://epubs.siam.org/doi/10.1137/0136016`
    -> `https://epubs.siam.org/doi/epdf/10.1137/0136016`
    -> `https://epubs.siam.org/doi/pdf/10.1137/0136016?download=true`
- **arXiv**: `https://doi.org/10.48550/arXiv.2207.03579` ✅
    -> `https://arxiv.org/abs/2207.03579`
    -> `https://arxiv.org/pdf/2207.03579`

- **journals.aps.org/**: `https://doi.org/10.1103/PHYSREVE.76.056709` ✅
    <!-- Wrong? -->
    <!-- -> `https://link.aps.org/doi/10.1103/PhysRevE.76.056709` -->
    -> `https://journals.aps.org/pre/abstract/10.1103/PhysRevE.76.056709`
    -> `https://journals.aps.org/pre/pdf/10.1103/PhysRevE.76.056709`

- **elsevier**: `https://doi.org/10.1016/J.PHYSA.2014.05.073`
    -> `https://www.sciencedirect.com/science/article/abs/pii/S037843711400466X?via%3Dihub`

**Difficult:**

- **Sage**: `10.1068/b306` — tokenized, needs headless browser
- **IOP**: `10.1088/1755-1315/526/1/012190` — reCAPTCHA redirect, use `auto_open_doi_on_fail`

## 长期目标

- [ ] CF bypass server 支持 headed 模式 + captcha 检测，弹出浏览器窗口让用户手动验证后自动继续下载
- [ ] Sage headless browser handler
- [ ] `{journal}` 占位符支持
- [ ] 状态浮窗透明背景
- [ ] 批量下载 / 全部下载按钮
