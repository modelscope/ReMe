#!/usr/bin/env python3
"""
MinerU PDF 处理器
返回 Markdown 内容和结构化的 content_list
"""

import os
import json
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Union
import platform
import re


class MinerUPDFProcessor:
    """
    基于 MinerU 的 PDF 处理器
    仿照 RAGAnything 的处理逻辑，但独立使用 MinerU
    """

    def __init__(self, log_level: str = "INFO"):
        """
        初始化处理器

        Args:
            log_level: 日志级别 ("DEBUG", "INFO", "WARNING", "ERROR")
        """
        # 设置日志
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        # 检查 MinerU 安装
        if not self.check_mineru_installation():
            raise RuntimeError(
                "MinerU 未正确安装。请使用以下命令安装：\n"
                "pip install -U 'mineru[core]' 或 uv pip install -U 'mineru[core]'"
            )

    def check_mineru_installation(self) -> bool:
        """检查 MinerU 是否正确安装"""
        try:
            subprocess_kwargs = {
                "capture_output": True,
                "text": True,
                "check": True,
                "encoding": "utf-8",
                "errors": "ignore",
            }

            # Windows 下隐藏控制台窗口
            if platform.system() == "Windows":
                subprocess_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(["mineru", "--version"], **subprocess_kwargs)
            self.logger.debug(f"MinerU 版本: {result.stdout.strip()}")
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
        运行 MinerU 命令行工具

        Args:
            input_path: 输入文件路径
            output_dir: 输出目录路径
            method: 解析方法 (auto, txt, ocr)
            lang: 文档语言，用于 OCR 优化
            backend: 解析后端
            start_page: 起始页码 (0-based)
            end_page: 结束页码 (0-based)
            formula: 启用公式解析
            table: 启用表格解析
            device: 推理设备
            source: 模型来源
            vlm_url: VLM 服务器 URL（当 backend 为 vlm-sglang-client 时需要）
        """
        cmd = [
            "mineru",
            "-p", str(input_path),
            "-o", str(output_dir),
            "-m", method,
            # "-b", backend,
            # "--source", source,
        ]

        # 添加可选参数
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
            subprocess_kwargs = {
                "capture_output": True,
                "text": True,
                "check": True,
                "encoding": "utf-8",
                "errors": "ignore",
            }

            # Windows 下隐藏控制台窗口
            if platform.system() == "Windows":
                subprocess_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            self.logger.info(f"执行 MinerU 命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, **subprocess_kwargs)

            self.logger.info("MinerU 命令执行成功")
            if result.stdout:
                self.logger.debug(f"MinerU 输出: {result.stdout}")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"MinerU 命令执行错误: {e}")
            if e.stderr:
                self.logger.error(f"错误详情: {e.stderr}")
            raise
        except FileNotFoundError:
            raise RuntimeError(
                "mineru 命令未找到。请确保 MinerU 2.0 已正确安装：\n"
                "pip install -U 'mineru[core]' 或 uv pip install -U 'mineru[core]'"
            )

    def _read_output_files(
            self,
            output_dir: Path,
            file_stem: str,
            method: str = "auto"
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        读取 MinerU 生成的输出文件

        Args:
            output_dir: 输出目录
            file_stem: 文件名（不含扩展名）
            method: 解析方法

        Returns:
            Tuple[List[Dict[str, Any]], str]: (content_list, markdown_content)
        """
        # 查找生成的文件
        md_file = output_dir / f"{file_stem}.md"
        json_file = output_dir / f"{file_stem}_content_list.json"
        images_base_dir = output_dir

        # 检查子目录结构
        file_stem_subdir = output_dir / file_stem
        if file_stem_subdir.exists():
            md_file = file_stem_subdir / method / f"{file_stem}.md"
            json_file = file_stem_subdir / method / f"{file_stem}_content_list.json"
            images_base_dir = file_stem_subdir / method

        # 读取 Markdown 内容
        md_content = ""
        if md_file.exists():
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    md_content = f.read()
                self.logger.info(f"成功读取 Markdown 文件: {md_file}")
            except Exception as e:
                self.logger.warning(f"无法读取 Markdown 文件 {md_file}: {e}")
        else:
            self.logger.warning(f"Markdown 文件不存在: {md_file}")

        # 读取 JSON 内容列表
        content_list = []
        if json_file.exists():
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    content_list = json.load(f)

                # 修复相对路径为绝对路径
                self.logger.info(f"修复图片路径，基础目录: {images_base_dir}")
                for item in content_list:
                    if isinstance(item, dict):
                        for field_name in ["img_path", "table_img_path", "equation_img_path"]:
                            if field_name in item and item[field_name]:
                                img_path = item[field_name]
                                if not os.path.isabs(img_path):
                                    absolute_img_path = (images_base_dir / img_path).resolve()
                                    item[field_name] = str(absolute_img_path)
                                    self.logger.debug(f"更新 {field_name}: {img_path} -> {item[field_name]}")

                self.logger.info(f"成功读取 JSON 文件: {json_file}, 包含 {len(content_list)} 个内容块")

            except Exception as e:
                self.logger.warning(f"无法读取 JSON 文件 {json_file}: {e}")
        else:
            self.logger.warning(f"JSON 文件不存在: {json_file}")

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
        处理 PDF 文件

        Args:
            pdf_path: PDF 文件路径
            output_dir: 输出目录路径（可选，默认在 PDF 文件同目录下创建）
            method: 解析方法 ("auto", "txt", "ocr")
            lang: 文档语言，用于 OCR 优化 (如 "ch", "en", "ja")
            backend: 解析后端 ("pipeline", "vlm-transformers", "vlm-sglang-engine", "vlm-sglang-client")
            **kwargs: 其他 MinerU 参数

        Returns:
            Tuple[List[Dict[str, Any]], str]: (content_list, markdown_content)

        Raises:
            FileNotFoundError: PDF 文件不存在
            RuntimeError: MinerU 处理失败
        """
        # 转换为 Path 对象
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

        if not pdf_path.suffix.lower() == '.pdf':
            raise ValueError(f"文件不是 PDF 格式: {pdf_path}")

        name_without_suffix = pdf_path.stem

        # 准备输出目录
        if output_dir:
            base_output_dir = Path(output_dir)
        else:
            base_output_dir = pdf_path.parent / "mineru_output"

        base_output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 运行 MinerU 命令
            self.logger.info(f"开始处理 PDF 文件: {pdf_path}")

            self._run_mineru_command(
                input_path=pdf_path,
                output_dir=base_output_dir,
                method=method,
                lang=lang,
                backend=backend,
                **kwargs
            )

            # 读取生成的输出文件
            backend_method = method
            if backend.startswith("vlm-"):
                backend_method = "vlm"

            content_list, markdown_content = self._read_output_files(
                base_output_dir, name_without_suffix, method=backend_method
            )

            # 统计处理结果
            content_stats = {}
            for item in content_list:
                if isinstance(item, dict):
                    content_type = item.get("type", "unknown")
                    content_stats[content_type] = content_stats.get(content_type, 0) + 1

            self.logger.info(f"PDF 处理完成! 提取了 {len(content_list)} 个内容块")
            self.logger.info("内容类型统计:")
            for content_type, count in content_stats.items():
                self.logger.info(f"  - {content_type}: {count}")

            return content_list, markdown_content

        except Exception as e:
            self.logger.error(f"处理 PDF 文件时出错: {str(e)}")
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
        保存处理结果到文件

        Args:
            content_list: 内容列表
            markdown_content: Markdown 内容
            output_path: 输出路径（不含扩展名）
            save_markdown: 是否保存 Markdown 文件
            save_json: 是否保存 JSON 文件
            indent: JSON 文件缩进

        Returns:
            Dict[str, Path]: 保存的文件路径字典
        """
        output_path = Path(output_path)
        saved_files = {}

        try:
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存 Markdown 文件
            if save_markdown and markdown_content:
                md_path = output_path.with_suffix('.md')
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                saved_files['markdown'] = md_path
                self.logger.info(f"Markdown 文件已保存: {md_path}")

            # 保存 JSON 文件
            if save_json and content_list:
                json_path = output_path.with_suffix('.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(content_list, f, indent=indent, ensure_ascii=False)
                saved_files['json'] = json_path
                self.logger.info(f"JSON 文件已保存: {json_path}")

            return saved_files

        except Exception as e:
            self.logger.error(f"保存文件时出错: {e}")
            raise


def chunk_pdf_content(content_list: List[Dict[str, Any]], max_length: int = 4000) -> List[str]:
    """
    将MinerU解析的content_list分割成指定长度的文本块

    Args:
        content_list: MinerU解析的内容列表
        max_length: 每个chunk的最大字符长度

    Returns:
        List[str]: 分块后的文本列表，每个文本都带有chunk标记
    """

    def extract_text(item):
        """提取单个item的文本"""
        if item.get("type") == "text":
            text = item.get("text", "").strip()
            if not text:
                return ""
            # 如果是标题，添加#标记
            level = item.get("text_level", 0)
            if level > 0:
                return f"{'#' * min(level, 6)} {text}"
            return text

        elif item.get("type") == "table":
            parts = []
            if item.get("table_caption"):
                parts.append("表格: " + " | ".join(item["table_caption"]))
            if item.get("table_body"):
                # 简单清理HTML标签
                table_text = re.sub(r'<[^>]+>', ' | ', item["table_body"])
                table_text = re.sub(r'\s+', ' ', table_text).strip()
                parts.append(table_text)
            return "\n".join(parts) if parts else ""

        elif item.get("type") == "image":
            if item.get("image_caption"):
                return "图片: " + " | ".join(item["image_caption"])
            return ""

        return ""

    # 提取所有文本
    all_text = ""
    for item in content_list:
        text = extract_text(item)
        if text.strip():
            all_text += text + "\n"

    if not all_text.strip():
        return []

    # 分割成chunks
    chunks = []
    current_chunk = ""

    for line in all_text.split('\n'):
        if len(current_chunk) + len(line) + 1 > max_length and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = line
        else:
            current_chunk += line + "\n" if current_chunk else line

    # 添加最后一个chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # 添加标记
    total_chunks = len(chunks)
    marked_chunks = []
    for i, chunk in enumerate(chunks):
        header = f"=== CHUNK {i + 1}/{total_chunks} ({len(chunk)}字符) ===\n"
        marked_chunks.append(header + chunk)

    return marked_chunks


def main():
    """主函数 - 直接处理 PDF 文件"""

    # 配置输入和输出路径
    input_pdf_path = "/Users/dengjiaji/Downloads/bandaoti_research.pdf"  # 修改为你的 PDF 文件路径
    output_dir = "/Users/dengjiaji/Downloads/bandaoti_research"  # 修改为你的输出目录

    try:
        # 创建处理器
        processor = MinerUPDFProcessor(log_level="INFO")

        # 处理 PDF 文件（使用默认参数）
        print(f"开始处理 PDF: {input_pdf_path}")
        content_list, markdown_content = processor.process_pdf(
            pdf_path=input_pdf_path,
            output_dir=output_dir,
            method="auto",  # 自动选择最佳解析方法
            backend="pipeline"  # 使用默认后端
        )

        # 保存结果到输出目录
        # output_base = Path(output_dir) / Path(input_pdf_path).stem
        # saved_files = processor.save_results(
        #     content_list=content_list,
        #     markdown_content=markdown_content,
        #     output_path=output_base
        # )

        # 显示结果
        print(f"\n✅ 处理完成!")
        print(f"📄 提取内容块数量: {len(content_list)}")
        print(f"📝 Markdown 内容长度: {len(markdown_content)} 字符")
        print(f"\n💾 保存的文件:")
        # for file_type, file_path in saved_files.items():
        #     print(f"  {file_type}: {file_path}")

        # 显示内容类型统计
        content_stats = {}
        for item in content_list:
            if isinstance(item, dict):
                content_type = item.get("type", "unknown")
                content_stats[content_type] = content_stats.get(content_type, 0) + 1

        print(f"\n📊 内容类型统计:")
        for content_type, count in content_stats.items():
            print(f"  {content_type}: {count}")

        return content_list, markdown_content

    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}")
        print("请检查 input_pdf_path 是否正确")
        return None, None
    except Exception as e:
        print(f"❌ 处理错误: {e}")
        return None, None


if __name__ == "__main__":
    # main()
    with open("/Users/dengjiaji/Downloads/bandaoti_research/bandaoti_research/auto/bandaoti_research_content_list.json", 'r', encoding='utf-8') as f:
        content_list = json.load(f)

    # 生成chunks
    chunks = chunk_pdf_content(content_list, max_length=10000)
    print("len(chunks)", len(chunks))
