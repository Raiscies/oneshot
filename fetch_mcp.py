import requests
import re
import json

url = 'https://platform.minimaxi.com/docs/token-plan/mcp-guide'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
r = requests.get(url, headers=headers, timeout=10)
text = r.text

print('=== MiniMax MCP 配置信息 ===')
print(f'Status: {r.status_code}')
print(f'Content Length: {len(text)}')
print()

# 查找Cline相关部分
print('--- Searching for Cline Config ---')
cline_section = re.findall(r'Cline.{0,5000}', text, re.DOTALL)
if cline_section:
    for section in cline_section[:3]:
        # 清理HTML标签
        clean = re.sub(r'<[^>]+>', '', section)
        clean = clean.replace('\\n', '\n').strip()
        if len(clean) > 50:
            print(clean[:1000])
            print('---')

# 查找npx命令
print('\n--- npx commands ---')
npx_matches = re.findall(r'npx[^<>"\']{0,300}', text)
for m in npx_matches[:5]:
    clean = re.sub(r'<[^>]+>', '', m).strip()
    if clean:
        print(clean[:200])
        print()


