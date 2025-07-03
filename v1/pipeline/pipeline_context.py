from concurrent.futures import ThreadPoolExecutor


class PipelineContext(object):

    def __init__(self):
        self.thread_pool: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=10)