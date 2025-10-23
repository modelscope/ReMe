---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.11.5
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Installation

### Install from PyPI (Recommended)

```bash
pip install reme-ai
```

### Install from Source

```bash
git clone https://github.com/modelscope/ReMe.git
cd ReMe
pip install .
```

### Environment Configuration

Copy `example.env` to .env and modify the corresponding parameters:

```bash
FLOW_APP_NAME=ReMe
FLOW_LLM_API_KEY=sk-xxxx
FLOW_LLM_BASE_URL=https://xxxx/v1
FLOW_EMBEDDING_API_KEY=sk-xxxx
FLOW_EMBEDDING_BASE_URL=https://xxxx/v1
```

You’ve completed the installation! Head over to [quick start](quick_start.md) to see how to start using Reme quickly.