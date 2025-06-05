import re


def get_html_match_content(content: str, key: str):
    pattern = rf"<{key}>(.*?)</{key}>"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1)
    return None
