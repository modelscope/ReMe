#!/usr/bin/env python3
"""
MinerU PDF Processor

A comprehensive PDF processing utility that leverages MinerU for extracting structured content
from PDF documents. Returns both Markdown content and structured content lists for further processing.

This processor provides a high-level interface to MinerU's command-line tools, handling
file I/O, error management, and result parsing automatically.
"""

import json
import logging
import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Union


class MinerUPDFProcessor:
    """
    MinerU-based PDF Processing Engine
    
    A robust PDF processor that wraps MinerU functionality to extract structured content
    from PDF documents. Inspired by RAGAnything's processing logic but operates independently
    with MinerU as the core engine.
    
    Features:
    - Automatic MinerU installation validation
    - Multiple parsing methods (auto, txt, ocr)
    - Language-specific OCR optimization
    - Structured content extraction with metadata
    - Image path resolution and management
    - Comprehensive error handling and logging
    
    Example:
        processor = MinerUPDFProcessor(log_level="INFO")
        content_list, markdown = processor.process_pdf("document.pdf")
    """

    def __init__(self, log_level: str = "INFO"):
        """
        Initialize the PDF processor with logging configuration.

        Args:
            log_level (str): Logging level for the processor. 
                           Options: "DEBUG", "INFO", "WARNING", "ERROR"
                           
        Raises:
            RuntimeError: If MinerU is not properly installed or accessible
        """
        # Configure logging system
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        # Validate MinerU installation before proceeding
        if not self.check_mineru_installation():
            raise RuntimeError(
                "MinerU is not properly installed. Please install using:\n"
                "pip install -U 'mineru[core]' or uv pip install -U 'mineru[core]'"
            )

    @classmethod
    def create_with_defaults(cls, log_level: str = "INFO") -> "MinerUPDFProcessor":
        """
        Create a MinerUPDFProcessor instance with default settings.
        
        Convenience method for quick instantiation with standard configuration.
        
        Args:
            log_level (str): Logging level (default: "INFO")
            
        Returns:
            MinerUPDFProcessor: Configured processor instance
        """
        return cls(log_level=log_level)

    def check_mineru_installation(self) -> bool:
        """
        Verify that MinerU is properly installed and accessible.
        
        Attempts to run the MinerU command-line tool to check its availability
        and version information.
        
        Returns:
            bool: True if MinerU is properly installed, False otherwise
        """
        try:
            # Configure subprocess parameters for cross-platform compatibility
            subprocess_kwargs = {
                "capture_output": True,
                "text": True,
                "check": True,
                "encoding": "utf-8",
                "errors": "ignore",
            }

            # Hide console window on Windows systems
            if platform.system() == "Windows":
                subprocess_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            # Execute version check command
            result = subprocess.run(["mineru", "--version"], **subprocess_kwargs)
            self.logger.debug(f"MinerU version detected: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _run_mineru_command(
            self,
            input_path: Union[str, Path],
            output_dir: Union[str, Path],
            method: str = "auto",
            lang: Optional[str] = None,
            backend: str = "pipeline",
            start_page: Optional[int] = None,
            end_page: Optional[int] = None,
            formula: bool = True,
            table: bool = True,
            device: Optional[str] = None,
            source: str = "modelscope",
            vlm_url: Optional[str] = None,
    ) -> None:
        """
        Execute MinerU command-line tool with specified parameters.
        
        This method constructs and executes the MinerU command with all provided
        options, handling cross-platform subprocess execution and error management.

        Args:
            input_path (Union[str, Path]): Path to the input PDF file
            output_dir (Union[str, Path]): Directory path for output files
            method (str): Parsing method - "auto", "txt", or "ocr"
            lang (Optional[str]): Document language for OCR optimization (e.g., "en", "ch", "ja")
            backend (str): Processing backend to use
            start_page (Optional[int]): Starting page number (0-based indexing)
            end_page (Optional[int]): Ending page number (0-based indexing)
            formula (bool): Enable mathematical formula parsing
            table (bool): Enable table structure parsing
            device (Optional[str]): Computing device for inference (e.g., "cuda", "cpu")
            source (str): Model source repository
            vlm_url (Optional[str]): VLM server URL (required for vlm-sglang-client backend)
            
        Raises:
            subprocess.CalledProcessError: If MinerU command execution fails
            FileNotFoundError: If MinerU executable is not found
            RuntimeError: If MinerU is not properly installed
        """
        # Build base command with required parameters
        cmd = [
            "mineru",
            "-p", str(input_path),
            "-o", str(output_dir),
            "-m", method,
            # Note: backend and source parameters are commented out as they may not be
            # available in all MinerU versions or configurations
            # "-b", backend,
            # "--source", source,
        ]

        # Add optional parameters if specified
        if lang:
            cmd.extend(["-l", lang])
        if start_page is not None:
            cmd.extend(["-s", str(start_page)])
        if end_page is not None:
            cmd.extend(["-e", str(end_page)])
        if not formula:
            cmd.extend(["-f", "false"])
        if not table:
            cmd.extend(["-t", "false"])
        if device:
            cmd.extend(["-d", device])
        if vlm_url:
            cmd.extend(["-u", vlm_url])

        try:
            # Configure subprocess execution parameters
            subprocess_kwargs = {
                "capture_output": True,
                "text": True,
                "check": True,
                "encoding": "utf-8",
                "errors": "ignore",
            }

            # Hide console window on Windows systems
            if platform.system() == "Windows":
                subprocess_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            self.logger.info(f"Executing MinerU command: {' '.join(cmd)}")
            result = subprocess.run(cmd, **subprocess_kwargs)

            self.logger.info("MinerU command executed successfully")
            if result.stdout:
                self.logger.debug(f"MinerU output: {result.stdout}")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"MinerU command execution failed: {e}")
            if e.stderr:
                self.logger.error(f"Error details: {e.stderr}")
            raise
        except FileNotFoundError:
            raise RuntimeError(
                "MinerU command not found. Please ensure MinerU 2.0 is properly installed:\n"
                "pip install -U 'mineru[core]' or uv pip install -U 'mineru[core]'"
            )

    def _read_output_files(
            self,
            output_dir: Path,
            file_stem: str,
            method: str = "auto"
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Read and parse MinerU-generated output files.
        
        This method locates and reads the Markdown and JSON files generated by MinerU,
        handling different directory structures and resolving image paths to absolute paths.

        Args:
            output_dir (Path): Directory containing the MinerU output files
            file_stem (str): Base filename without extension
            method (str): Parsing method used ("auto", "txt", "ocr", "vlm")

        Returns:
            Tuple[List[Dict[str, Any]], str]: A tuple containing:
                - content_list: Structured content list with metadata
                - markdown_content: Raw markdown text content
        """
        # Locate generated output files - handle both flat and nested directory structures
        md_file = output_dir / f"{file_stem}.md"
        json_file = output_dir / f"{file_stem}_content_list.json"
        images_base_dir = output_dir

        # Check for nested subdirectory structure (common with newer MinerU versions)
        file_stem_subdir = output_dir / file_stem
        if file_stem_subdir.exists():
            md_file = file_stem_subdir / method / f"{file_stem}.md"
            json_file = file_stem_subdir / method / f"{file_stem}_content_list.json"
            images_base_dir = file_stem_subdir / method

        # Read Markdown content
        md_content = ""
        if md_file.exists():
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    md_content = f.read()
                self.logger.info(f"Successfully read Markdown file: {md_file}")
            except Exception as e:
                self.logger.warning(f"Failed to read Markdown file {md_file}: {e}")
        else:
            self.logger.warning(f"Markdown file not found: {md_file}")

        # Read structured content list from JSON
        content_list = []
        if json_file.exists():
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    content_list = json.load(f)

                # Convert relative image paths to absolute paths for proper access
                self.logger.info(f"Resolving image paths relative to: {images_base_dir}")
                for item in content_list:
                    if isinstance(item, dict):
                        # Process various image path fields that may be present
                        for field_name in ["img_path", "table_img_path", "equation_img_path"]:
                            if field_name in item and item[field_name]:
                                img_path = item[field_name]
                                if not os.path.isabs(img_path):
                                    absolute_img_path = (images_base_dir / img_path).resolve()
                                    item[field_name] = str(absolute_img_path)
                                    self.logger.debug(f"Updated {field_name}: {img_path} -> {item[field_name]}")

                self.logger.info(f"Successfully read JSON file: {json_file}, containing {len(content_list)} content blocks")

            except Exception as e:
                self.logger.warning(f"Failed to read JSON file {json_file}: {e}")
        else:
            self.logger.warning(f"JSON file not found: {json_file}")

        return content_list, md_content

    def process_pdf(
            self,
            pdf_path: Union[str, Path],
            output_dir: Optional[Union[str, Path]] = None,
            method: str = "auto",
            lang: Optional[str] = None,
            backend: str = "pipeline",
            **kwargs
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Process a PDF file and extract structured content using MinerU.
        
        This is the main entry point for PDF processing. It validates input,
        executes MinerU processing, and returns both structured content and markdown.

        Args:
            pdf_path (Union[str, Path]): Path to the input PDF file
            output_dir (Optional[Union[str, Path]]): Output directory path. 
                                                   If None, creates 'mineru_output' in PDF's directory
            method (str): Parsing method - "auto" (recommended), "txt", or "ocr"
            lang (Optional[str]): Document language for OCR optimization 
                                (e.g., "ch" for Chinese, "en" for English, "ja" for Japanese)
            backend (str): Processing backend - "pipeline", "vlm-transformers", 
                         "vlm-sglang-engine", or "vlm-sglang-client"
            **kwargs: Additional MinerU parameters (start_page, end_page, formula, table, etc.)

        Returns:
            Tuple[List[Dict[str, Any]], str]: A tuple containing:
                - content_list: Structured list of content blocks with metadata
                - markdown_content: Complete document in Markdown format

        Raises:
            FileNotFoundError: If the specified PDF file does not exist
            ValueError: If the file is not a valid PDF format
            RuntimeError: If MinerU processing fails or encounters errors
        """
        # Convert to Path object and validate input
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file does not exist: {pdf_path}")

        if not pdf_path.suffix.lower() == '.pdf':
            raise ValueError(f"File is not a PDF format: {pdf_path}")

        name_without_suffix = pdf_path.stem

        # Prepare output directory
        if output_dir:
            base_output_dir = Path(output_dir)
        else:
            base_output_dir = pdf_path.parent / "mineru_output"

        base_output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Execute MinerU processing
            self.logger.info(f"Starting PDF processing: {pdf_path}")

            self._run_mineru_command(
                input_path=pdf_path,
                output_dir=base_output_dir,
                method=method,
                lang=lang,
                backend=backend,
                **kwargs
            )

            # Read generated output files
            backend_method = method
            if backend.startswith("vlm-"):
                backend_method = "vlm"

            content_list, markdown_content = self._read_output_files(
                base_output_dir, name_without_suffix, method=backend_method
            )

            # Generate processing statistics
            content_stats = {}
            for item in content_list:
                if isinstance(item, dict):
                    content_type = item.get("type", "unknown")
                    content_stats[content_type] = content_stats.get(content_type, 0) + 1

            self.logger.info(f"PDF processing completed! Extracted {len(content_list)} content blocks")
            self.logger.info("Content type statistics:")
            for content_type, count in content_stats.items():
                self.logger.info(f"  - {content_type}: {count}")

            return content_list, markdown_content

        except Exception as e:
            self.logger.error(f"Error occurred during PDF processing: {str(e)}")
            raise

    def save_results(
            self,
            content_list: List[Dict[str, Any]],
            markdown_content: str,
            output_path: Union[str, Path],
            save_markdown: bool = True,
            save_json: bool = True,
            indent: int = 2
    ) -> Dict[str, Path]:
        """
        Save processing results to files.
        
        Saves the extracted content in both JSON (structured) and Markdown (text) formats
        for different use cases and downstream processing needs.

        Args:
            content_list (List[Dict[str, Any]]): Structured content list with metadata
            markdown_content (str): Complete document in Markdown format
            output_path (Union[str, Path]): Output file path (without extension)
            save_markdown (bool): Whether to save Markdown file
            save_json (bool): Whether to save JSON file with structured content
            indent (int): JSON file indentation for readability

        Returns:
            Dict[str, Path]: Dictionary mapping file types to their saved paths
                           Keys: 'markdown', 'json' (if respective files were saved)
                           
        Raises:
            Exception: If file writing operations fail
        """
        output_path = Path(output_path)
        saved_files = {}

        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save Markdown file
            if save_markdown and markdown_content:
                md_path = output_path.with_suffix('.md')
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                saved_files['markdown'] = md_path
                self.logger.info(f"Markdown file saved: {md_path}")

            # Save JSON file with structured content
            if save_json and content_list:
                json_path = output_path.with_suffix('.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(content_list, f, indent=indent, ensure_ascii=False)
                saved_files['json'] = json_path
                self.logger.info(f"JSON file saved: {json_path}")

            return saved_files

        except Exception as e:
            self.logger.error(f"Error occurred while saving files: {e}")
            raise

    @staticmethod
    def get_content_statistics(content_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate detailed statistics about the processed content.
        
        Analyzes the content list to provide insights into document structure,
        content types, and processing results.
        
        Args:
            content_list (List[Dict[str, Any]]): Structured content list from MinerU
            
        Returns:
            Dict[str, Any]: Dictionary containing various statistics:
                - total_blocks: Total number of content blocks
                - content_types: Count of each content type
                - text_stats: Text-specific statistics (characters, words, etc.)
                - image_count: Number of images found
                - table_count: Number of tables found
        """
        stats = {
            "total_blocks": len(content_list),
            "content_types": {},
            "text_stats": {"total_characters": 0, "total_words": 0, "title_levels": {}},
            "image_count": 0,
            "table_count": 0,
            "has_formulas": False
        }
        
        for item in content_list:
            if not isinstance(item, dict):
                continue
                
            content_type = item.get("type", "unknown")
            stats["content_types"][content_type] = stats["content_types"].get(content_type, 0) + 1
            
            if content_type == "text":
                text = item.get("text", "")
                stats["text_stats"]["total_characters"] += len(text)
                stats["text_stats"]["total_words"] += len(text.split())
                
                level = item.get("text_level", 0)
                if level > 0:
                    stats["text_stats"]["title_levels"][level] = stats["text_stats"]["title_levels"].get(level, 0) + 1
                    
            elif content_type == "image":
                stats["image_count"] += 1
                
            elif content_type == "table":
                stats["table_count"] += 1
                
            elif content_type == "formula":
                stats["has_formulas"] = True
        
        return stats

    def validate_output_quality(self, content_list: List[Dict[str, Any]], markdown_content: str) -> Dict[str, Any]:
        """
        Validate the quality and completeness of the processing output.
        
        Performs various checks to ensure the processed content meets quality standards
        and provides warnings or suggestions for improvement.
        
        Args:
            content_list (List[Dict[str, Any]]): Structured content list
            markdown_content (str): Markdown content string
            
        Returns:
            Dict[str, Any]: Validation results containing:
                - is_valid: Overall validation status
                - warnings: List of warning messages
                - suggestions: List of improvement suggestions
                - quality_score: Numeric quality score (0-100)
        """
        validation = {
            "is_valid": True,
            "warnings": [],
            "suggestions": [],
            "quality_score": 100
        }
        
        # Check if content was extracted
        if not content_list and not markdown_content.strip():
            validation["is_valid"] = False
            validation["warnings"].append("No content was extracted from the PDF")
            validation["quality_score"] = 0
            return validation
        
        # Check content diversity
        stats = self.get_content_statistics(content_list)
        if stats["total_blocks"] < 5:
            validation["warnings"].append("Very few content blocks extracted - document may be complex or image-heavy")
            validation["quality_score"] -= 20
        
        # Check text content ratio
        text_blocks = stats["content_types"].get("text", 0)
        if text_blocks == 0:
            validation["warnings"].append("No text blocks found - consider using OCR method for image-based PDFs")
            validation["quality_score"] -= 30
        elif text_blocks / stats["total_blocks"] < 0.3:
            validation["suggestions"].append("Low text content ratio - document may benefit from OCR processing")
            validation["quality_score"] -= 10
        
        # Check for images without processing
        if stats["image_count"] > 0 and stats["content_types"].get("text", 0) == 0:
            validation["suggestions"].append("Images detected but no text extracted - consider using VLM backend for image analysis")
        
        # Check markdown length vs content blocks
        if len(markdown_content.strip()) < 100 and stats["total_blocks"] > 10:
            validation["warnings"].append("Markdown content seems unusually short for the number of content blocks")
            validation["quality_score"] -= 15
        
        return validation


def chunk_pdf_content(content_list: List[Dict[str, Any]], max_length: int = 4000) -> List[str]:
    """
    Split MinerU-parsed content list into text chunks of specified length.
    
    This utility function converts structured content from MinerU into manageable
    text chunks suitable for downstream processing like embedding generation or
    language model input.

    Args:
        content_list (List[Dict[str, Any]]): MinerU-parsed structured content list
        max_length (int): Maximum character length per chunk (default: 4000)

    Returns:
        List[str]: List of text chunks, each prefixed with chunk metadata
                  including chunk number, total chunks, and character count
    """

    def extract_text(item: Dict[str, Any]) -> str:
        """
        Extract text content from a single content item.
        
        Handles different content types (text, table, image) and formats them
        appropriately for text-based processing.
        
        Args:
            item (Dict[str, Any]): Single content item from MinerU output
            
        Returns:
            str: Extracted and formatted text content
        """
        if item.get("type") == "text":
            text = item.get("text", "").strip()
            if not text:
                return ""
            # Add markdown header formatting for titles
            level = item.get("text_level", 0)
            if level > 0:
                return f"{'#' * min(level, 6)} {text}"
            return text

        elif item.get("type") == "table":
            parts = []
            if item.get("table_caption"):
                parts.append("Table: " + " | ".join(item["table_caption"]))
            if item.get("table_body"):
                # Simple HTML tag cleanup and formatting
                table_text = re.sub(r'<[^>]+>', ' | ', item["table_body"])
                table_text = re.sub(r'\s+', ' ', table_text).strip()
                parts.append(table_text)
            return "\n".join(parts) if parts else ""

        elif item.get("type") == "image":
            if item.get("image_caption"):
                return "Image: " + " | ".join(item["image_caption"])
            return ""

        return ""

    # Extract all text content from the structured list
    all_text = ""
    for item in content_list:
        text = extract_text(item)
        if text.strip():
            all_text += text + "\n"

    if not all_text.strip():
        return []

    # Split into chunks based on max_length
    chunks = []
    current_chunk = ""

    for line in all_text.split('\n'):
        # Check if adding this line would exceed max_length
        if len(current_chunk) + len(line) + 1 > max_length and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = line
        else:
            current_chunk += line + "\n" if current_chunk else line

    # Add the final chunk if it contains content
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Add chunk metadata headers
    total_chunks = len(chunks)
    marked_chunks = []
    for i, chunk in enumerate(chunks):
        header = f"=== CHUNK {i + 1}/{total_chunks} ({len(chunk)} characters) ===\n"
        marked_chunks.append(header + chunk)

    return marked_chunks


# Example usage and demonstration
if __name__ == "__main__":
    """
    Example usage of the MinerUPDFProcessor class.
    
    This example demonstrates the basic workflow for processing a PDF file
    and working with the extracted content.
    """
    import sys
    
    # Example usage
    def example_usage():
        """Demonstrate basic PDF processing workflow."""
        try:
            # Initialize processor
            processor = MinerUPDFProcessor.create_with_defaults(log_level="INFO")
            
            # Example PDF path (replace with actual PDF file)
            pdf_path = "example_document.pdf"
            
            if not Path(pdf_path).exists():
                print(f"Example PDF file not found: {pdf_path}")
                print("Please provide a valid PDF file path to test the processor.")
                return
            
            # Process PDF with different methods
            print("Processing PDF with auto method...")
            content_list, markdown_content = processor.process_pdf(
                pdf_path=pdf_path,
                method="auto",
                lang="en"  # Specify language for better OCR results
            )
            
            # Generate statistics
            stats = processor.get_content_statistics(content_list)
            print(f"Processing Statistics:")
            print(f"  Total blocks: {stats['total_blocks']}")
            print(f"  Content types: {stats['content_types']}")
            print(f"  Text characters: {stats['text_stats']['total_characters']}")
            print(f"  Text words: {stats['text_stats']['total_words']}")
            
            # Validate output quality
            validation = processor.validate_output_quality(content_list, markdown_content)
            print(f"Quality Score: {validation['quality_score']}/100")
            if validation['warnings']:
                print("Warnings:", validation['warnings'])
            if validation['suggestions']:
                print("Suggestions:", validation['suggestions'])
            
            # Save results
            output_path = Path(pdf_path).stem + "_processed"
            saved_files = processor.save_results(
                content_list=content_list,
                markdown_content=markdown_content,
                output_path=output_path
            )
            print(f"Results saved to: {saved_files}")
            
            # Create text chunks for downstream processing
            chunks = chunk_pdf_content(content_list, max_length=2000)
            print(f"Created {len(chunks)} text chunks")
            
            # Display first chunk as example
            if chunks:
                print("First chunk preview:")
                print(chunks[0][:200] + "..." if len(chunks[0]) > 200 else chunks[0])
                
        except Exception as e:
            print(f"Error during processing: {e}")
            sys.exit(1)
    
    # Run example if script is executed directly
    example_usage()
