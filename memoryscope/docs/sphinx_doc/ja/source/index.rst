.. MemoryScope documentation master file, created by
   sphinx-quickstart on Fri Jan  5 17:53:54 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

:github_url: https://github.com/modelscope/memoryscope

MemoryScope ドキュメント
=========================

MemoryScopeに関するドキュメントへようこそ
-------------------------------

.. image:: ./docs/images/logo.png
    :align: center

MemoryScopeは、LLMチャットボットに強力で柔軟な長期記憶能力を提供し、長期記憶能力を構築するためのフレームワークを提供します。
MemoryScopeは、個人アシスタントや感情的な伴侶などの記憶シナリオに使用でき、長期記憶能力を通じてユーザーの基本情報やさまざまな習慣や好みを覚え続けることができます。
これにより、ユーザーはLLMを使用する際に徐々に「理解されている」感覚を体験することができます。

.. image:: docs/images/framework.png
    :align: center

フレームワーク
^^^^^^^^^^^^^^^^^^^^

💾 メモリデータベース: MemoryScopeは、システム内に記録されたすべての記憶片を保存するためのベクトルデータベース（デフォルトは*ElasticSearch*）を備えています。

🔧 ワーカーライブラリ: MemoryScopeは、長期記憶の能力を個々のワーカーに原子化し、クエリ情報のフィルタリング、観察の抽出、洞察の更新など、20以上のワーカーを含みます。

🛠️ オペレーションライブラリ: ワーカーパイプラインに基づいて、メモリサービスのオペレーションを構築し、メモリの取得やメモリの統合などの主要な機能を実現します。

- メモリの取得: ユーザークエリが到着すると、この操作は意味的に関連する記憶片を返します。
  クエリが時間に言及している場合は、対応する時間の記憶片も返します。
- メモリの統合: この操作は、一連のユーザークエリを受け取り、クエリから抽出された重要なユーザー情報を統合された*観察*としてメモリデータベースに保存します。
- 反映と再統合: 定期的に、この操作は新たに記録された*観察*を反映し、*洞察*を形成および更新します。
  その後、メモリの再統合を実行して、記憶片間の矛盾や重複が適切に処理されるようにします。

.. toctree::
   :maxdepth: 2
   :caption: MemoryScope チュートリアル

   MemoryScopeについて <README.md>
   インストール <docs/installation.md>
   CLIクライアント <examples/cli/CLI_README.md>
   簡単な使用法 <examples/api/simple_usages.ipynb>
   高度な使用法 <examples/advance/custom_operator.md>
   貢献 <docs/contribution.md>


.. toctree::
   :maxdepth: 6
   :caption: MemoryScope APIリファレンス

   API <docs/api.rst>
