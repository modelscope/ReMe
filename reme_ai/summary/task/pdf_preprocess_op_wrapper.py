from flowllm import C, BaseOp
from loguru import logger

from reme_ai.utils.miner_u_pdf_processor import MinerUPDFProcessor, chunk_pdf_content


@C.register_op()
class PDFPreprocessOp(BaseOp):
    file_path: str = __file__

    def execute(self):
        """Process PDF files using MinerU and chunk content"""
        pdf_path = self.context.get("pdf_path")
        output_dir = self.context.get("output_dir")
        
        if not pdf_path:
            logger.error("No PDF path provided in context")
            return

        # Process PDF
        processor = MinerUPDFProcessor(log_level="INFO")
        
        try:
            content_list, markdown_content = processor.process_pdf(
                pdf_path=pdf_path,
                output_dir=output_dir,
                method=self.op_params.get("method", "auto"),
                lang=self.op_params.get("lang"),
                backend=self.op_params.get("backend", "pipeline")
            )
            
            # Create chunks if requested
            chunks = []
            if self.op_params.get("create_chunks", True):
                max_length = self.op_params.get("max_chunk_length", 4000)
                chunks = chunk_pdf_content(content_list, max_length=max_length)
            
            # Store results in context
            self.context.pdf_content_list = content_list
            self.context.pdf_markdown_content = markdown_content
            self.context.pdf_chunks = chunks
            
            logger.info(f"PDF processing completed: {len(content_list)} content blocks, "
                       f"{len(chunks)} chunks, {len(markdown_content)} characters of markdown")
            
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            self.context.pdf_content_list = []
            self.context.pdf_markdown_content = ""
            self.context.pdf_chunks = []
