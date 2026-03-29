import requests
import re

url = 'https://platform.minimaxi.com/docs/token-plan/mcp-guide'
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
text = r.text

print('=== MiniMax MCP Guide Analysis ===')
print(f'Status: {r.status_code}')
print(f'Length: {len(text)}')
print()

# Find all <pre> tags which typically contain code blocks
pre_blocks = re.findall(r'<pre[^>]*>(.*?)</pre>', text, re.DOTALL)
print(f'Found {len(pre_blocks)} <pre> blocks')
print()

# Search for configuration related content
search_terms = ['minimax-coding-plan-mcp', 'MINIMAX_API_KEY', 'npx', 'mcpServers', 'command', 'args']
for term in search_terms:
    count = text.count(term)
    print(f'{term}: appears {count} times')

print()
print('=== All <pre> block contents ===')
for i, block in enumerate(pre_blocks[:20]):
    # Clean HTML tags
    clean = re.sub(r'<[^>]+>', '', block)
    clean = clean.replace('\\n', '\n').strip()
    if len(clean) > 20:
        print(f'--- Block {i+1} ({len(clean)} chars) ---')
        print(clean[:500])
        print()
