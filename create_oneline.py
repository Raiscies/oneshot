import os

# 创建单行版本
text = open('papers/test_file.txt', encoding='utf-8').read()
text = text.replace('\n', ' ').replace('\r', ' ')
with open('papers/test_file_oneline.txt', 'w', encoding='utf-8') as f:
    f.write(text)
print('Created papers/test_file_oneline.txt')

# 运行 anystyle find
os.system('ruby -S anystyle --stdout -f json find papers/test_file_oneline.txt > debug/anystyle_find_oneline.json 2>&1')
print('Done')
