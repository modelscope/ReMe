#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def analyze_corrupted_text(text):
    """分析乱码文本的字节构成"""
    print(f"分析文本: {text}")
    print(f"文本长度: {len(text)}")

    # 显示每个字符的Unicode码点
    print("字符分析:")
    for i, char in enumerate(text[:20]):  # 只显示前20个字符
        print(f"  {i}: '{char}' -> U+{ord(char):04X}")

    # 尝试不同的编码方式
    print("\n编码尝试:")

    try:
        # 方法1: Latin1 -> UTF-8
        bytes_latin1 = text.encode('latin1')
        result_utf8 = bytes_latin1.decode('utf-8')
        print(f"Latin1->UTF-8: {result_utf8}")
    except Exception as e:
        print(f"Latin1->UTF-8 失败: {e}")

    try:
        # 方法2: Latin1 -> GBK
        bytes_latin1 = text.encode('latin1')
        result_gbk = bytes_latin1.decode('gbk')
        print(f"Latin1->GBK: {result_gbk}")
    except Exception as e:
        print(f"Latin1->GBK 失败: {e}")

    try:
        # 方法3: CP1252 -> UTF-8
        bytes_cp1252 = text.encode('cp1252')
        result_utf8 = bytes_cp1252.decode('utf-8')
        print(f"CP1252->UTF-8: {result_utf8}")
    except Exception as e:
        print(f"CP1252->UTF-8 失败: {e}")

    # 显示原始字节
    try:
        raw_bytes = text.encode('latin1')
        print(f"\n原始字节 (Latin1): {raw_bytes}")
        print(f"字节十六进制: {raw_bytes.hex()}")
    except Exception as e:
        print(f"获取原始字节失败: {e}")


def main():
    """调试主函数"""
    test_texts = [
        "ä¸ºä»ä¹è¯´æçå»è¯è¿å¥ä¸­æå¸å±æç¹ï¼",
        "åçäºâäºä¸âæé´ä¸­å½ç»æµå¤è¯éªçä¹è§å¤æ­",
        "æçç§ææ°ï¼HSTECH.HIï¼åº¦æ¼æ¶4.45%"
    ]

    for i, text in enumerate(test_texts, 1):
        print(f"\n{'=' * 60}")
        print(f"测试 {i}")
        print('=' * 60)
        analyze_corrupted_text(text)


if __name__ == "__main__":
    main()
