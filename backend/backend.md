抓取加载: ingest.py 用各类 Loader 拉取数据（LangChain 文档/API、可选 PubMed）。例如 load_api_docs()、load_langchain_docs()。

解析清洗: 对网页类内容，parser.py 在 Loader 中作为 parsing_function 把 HTML 提取为纯文本/Markdown；这一步发生在 ingest 阶段内部，而不是单独“parser 再跑一次”。见 backend/ingest.py:33 与 backend/parser.py:6

切分与向量化: ingest.py 里切分文本并用 OpenAI Embeddings 生成向量。见 backend/ingest.py:110-123

入库索引: ingest.py 把向量写入 Weaviate 向量库。见 backend/ingest.py:118-125 和 backend/ingest.py:162-169

检索与回答: chain.py 作为服务端，通过 Weaviate 建检索器并调用 LLM 生成答案。见 backend/chain.py:137 和 backend/chain.py:1-20
