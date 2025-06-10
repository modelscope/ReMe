from experiencemaker.module.summarizer.base_summarizer import BaseSummarizer
from experiencemaker.module.summarizer.simple_summarizer import SimpleSummarizer
from experiencemaker.utils.registry import Registry

SUMMARIZER_REGISTRY = Registry[BaseSummarizer]("summarizer")
SUMMARIZER_REGISTRY.register(SimpleSummarizer, "simple")
