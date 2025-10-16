import tiktoken
enc = tiktoken.get_encoding("o200k_base")

# r = enc.encode("我爱吃西瓜，你说啥")
r = enc.encode("hello world aaaaaaaaaaaa")
print(len(r))