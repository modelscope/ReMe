[**English**](./README.md) | [**中文**](./README_ZH.md) | 日本語

# MemoryScope
<p align="center">
 <img src="./docs/images/logo.png" alt="MemoryScopeLogo" width="75%">
</p>
あなたのLLMチャットボットに強力で柔軟な長期記憶システムを装備しましょう。

[![](https://img.shields.io/badge/python-3.10+-blue)](https://pypi.org/project/memoryscope/)
[![](https://img.shields.io/badge/pypi-v0.1.1.0-blue?logo=pypi)](https://pypi.org/project/memoryscope/)
[![](https://img.shields.io/badge/license-Apache--2.0-black)](./LICENSE)
[![](https://img.shields.io/badge/Docs-English%7C%E4%B8%AD%E6%96%87-blue?logo=markdown)](https://modelscope.github.io/MemoryScope/en/index.html#welcome-to-memoryscope-tutorial)
[![](https://img.shields.io/badge/Docs-API_Reference-blue?logo=markdown)](https://modelscope.github.io/MemoryScope/en/docs/api.html)
[![](https://img.shields.io/badge/Contribute-Welcome-green)](https://modelscope.github.io/MemoryScope/en/docs/contribution.html)

----
## 📰 ニュース

- **[2024-09-10]** MemoryScope v0.1.1.0をリリースしました。 [PyPI](https://pypi.org/simple/memoryscope/)でも入手可能です！
----
## 🌟 MemoryScopeとは？
MemoryScopeは、LLMチャットボットに強力で柔軟な長期記憶能力を提供し、その能力を構築するためのフレームワークを提供します。
個人アシスタントや感情的な伴侶などのシナリオに適用でき、長期記憶を通じてユーザーの基本情報やさまざまな習慣や好みを覚え続けることができます。
これにより、ユーザーはLLMを使用する際に徐々に「理解されている」感覚を体験することができます。

### デモ
<p align="center">
 <img src="https://github.com/user-attachments/assets/1754c814-1342-4288-a8a3-74d0b40f59a6" alt="en_demo" width="75%">
</p>

### フレームワーク
<p align="center">
 <img src="./docs/images/framework.png" alt="Framework" width="75%">
</p>

💾 メモリデータベース: MemoryScopeは、システム内に記録されたすべての記憶片を保存するためのベクトルデータベース（デフォルトは*ElasticSearch*）を備えています。

🔧 ワーカーライブラリ: MemoryScopeは、長期記憶の能力を個々のワーカーに原子化し、クエリ情報のフィルタリング、観察の抽出、洞察の更新など、20以上のワーカーを含みます。

🛠️ オペレーションライブラリ: ワーカーパイプラインに基づいて、メモリサービスのオペレーションを構築し、メモリの取得やメモリの統合などの主要な機能を実現します。

- メモリの取得: ユーザークエリが到着すると、この操作は意味的に関連する記憶片を返します。
  クエリが時間に言及している場合は、対応する時間の記憶片も返します。
- メモリの統合: この操作は、一連のユーザークエリを受け取り、クエリから抽出された重要なユーザー情報を統合された*観察*としてメモリデータベースに保存します。
- 反映と再統合: 定期的に、この操作は新たに記録された*観察*を反映し、*洞察*を形成および更新します。
  その後、メモリの再統合を実行して、記憶片間の矛盾や重複が適切に処理されるようにします。

⚙️ ベストプラクティス:

- MemoryScopeは、長期記憶のコア機能に基づいて、長期記憶を持つ対話インターフェース（API）と長期記憶を持つコマンドライン対話の実践（CLI）を実装しています。
- MemoryScopeは、現在人気のあるエージェントフレームワーク（AutoGen、AgentScope）を組み合わせて、ベストプラクティスを提供します。

### 主な特徴

⚡ 低い応答時間（RT）:
- システム内のバックエンド操作（メモリの統合、反映と再統合）は、フロントエンド操作（メモリの取得）と分離されています。
- バックエンド操作は通常（および推奨される）キューに入れられるか、定期的に実行されるため、システムのユーザー応答時間（RT）はフロントエンド操作のみに依存し、約500ミリ秒です。

🌲 階層的で一貫性のある記憶:
- システムに保存される記憶片は階層構造になっており、*洞察*は同様のテーマの*観察*の集約から得られる高レベルの情報です。
- 記憶片間の矛盾や重複は定期的に処理され、一貫性が保たれます。
- ユーザーの虚偽の内容はフィルタリングされ、LLMの幻覚を避けることができます。

⏰ 時間感覚:
- メモリの取得とメモリの統合を実行する際に時間感覚があり、クエリが時間に言及している場合に正確な関連情報を取得できます。

----

## 💼 サポートされているモデルAPI

| バックエンド           | タスク       | サポートされているモデルの一部                                                  |
|-------------------|------------|------------------------------------------------------------------------|
| openai_backend    | Generation | gpt-4o, gpt-4o-mini, gpt-4, gpt-3.5-turbo                              |
|                   | Embedding  | text-embedding-ada-002, text-embedding-3-large, text-embedding-3-small |
| dashscope_backend | Generation | qwen-max, qwen-plus, qwen-plus, qwen2-72b-instruct                     |
|                   | Embedding  | text-embedding-v1, text-embedding-v2                                   |
|                   | Reranker   | gte-rerank                                                             |

将来的には、より多くのモデルインターフェースとローカルデプロイメントのLLMおよび埋め込みサービスをサポートする予定です。

## 🚀 インストール
インストール方法については、[Installation.md](docs/installation.md)を参照してください。

## 🍕 クイックスタート
- [簡単な使用法（クイックスタート）](./examples/api/simple_usages.ipynb)
- [AutoGenとの連携](./examples/api/autogen_example.md)
- [MemoryScopeチャットボットとのCLI](./examples/cli/README.md)
- [高度なカスタマイズ](./examples/advance/custom_operator.md)

## 💡 貢献

貢献は常に奨励されています！

プルリクエストをコミットする前に、このリポジトリにpre-commitフックをインストールすることを強くお勧めします。
これらのフックは、gitコミットを行うたびに実行される小さなハウスキーピングスクリプトであり、フォーマットとリンティングを自動的に処理します。
```shell
pip install -e .
pre-commit install
```

詳細については、[貢献ガイド](./docs/contribution.md)を参照してください。

## 📖 引用

MemoryScopeを論文で使用する場合は、以下の引用を追加してください：

```
@software{MemoryScope,
author = {Li Yu and 
          Tiancheng Qin and
          Qingxu Fu and
          Sen Huang and
          Xianzhe Xu and
          Zhaoyang Liu and
          Boyin Liu},
month = {09},
title = {{MemoryScope}},
url = {https://github.com/modelscope/MemoryScope},
year = {2024}
}
```
