import tiktoken

def count_tokens(text: str) -> int:
    """计算给定文本在指定模型下的 token 数量"""
    encoding = tiktoken.get_encoding("o200k_base")
    tokens = encoding.encode(text)
    return len(tokens)

# 示例使用
text = "你好，世界！Hello, world!"
token_count = count_tokens(text)
print(f"Token 数量: {token_count}")
print(len(text) / 4)
