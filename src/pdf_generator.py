import logging
from pathlib import Path
from playwright.sync_api import sync_playwright

from arguments_manager import ArgumentManager

logger = logging.getLogger(__name__)


class PDFGenerator:
    def generate(self, html_file_path: Path, pdf_file_path: Path):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                context = browser.new_context()
                page = context.new_page()
                page.goto(f"file://{html_file_path.absolute()}")
                page.pdf(
                    path=pdf_file_path,
                    format=ArgumentManager().paper_format,
                    landscape=True,
                    print_background=True,
                )
                browser.close()
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise
