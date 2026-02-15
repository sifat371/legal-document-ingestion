#!/usr/bin/env python3
"""
Legal Case PDF Ingestion Pipeline using Docling
================================================

Converts legal case PDFs to Markdown and structured JSON using Docling.
Extracts metadata (case number, court, judges) and generates processing reports.

Features:
- Docling PDF → Markdown + JSON conversion
- Regex-based metadata extraction
- UTF-8 safe (English + Bengali)
- Progress bars (tqdm)
- Comprehensive logging
- Error handling for corrupted PDFs
- Processing summary generation

Author: legalBuddy Team
License: MIT
"""

import json
import logging
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from docling.document_converter import DocumentConverter
from tqdm import tqdm


# ============================================================================
# Configuration
# ============================================================================

RAW_CASES_DIR = Path("data/raw_cases")
EXTRACTED_CASES_DIR = Path("data/extracted_cases")
SUMMARY_FILE = "processing_summary.json"

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class CaseMetadata:
    """Metadata extracted from legal case documents."""
    case_number: Optional[str] = None
    court: Optional[str] = None
    judges: List[str] = None
    district: Optional[str] = None
    case_type: Optional[str] = None
    parties: Dict[str, str] = None
    hearing_date: Optional[str] = None
    judgment_date: Optional[str] = None

    def __post_init__(self):
        if self.judges is None:
            self.judges = []
        if self.parties is None:
            self.parties = {}


@dataclass
class ProcessingResult:
    """Result of processing a single PDF."""
    input_file: str
    status: str  # "success" or "failed"
    markdown_output: Optional[str] = None
    json_output: Optional[str] = None
    metadata_output: Optional[str] = None
    error_message: Optional[str] = None
    word_count: int = 0
    char_count: int = 0


# ============================================================================
# Logging Setup
# ============================================================================

def setup_logging(log_level: int = logging.INFO) -> logging.Logger:
    """
    Configure logging with console and file handlers.
    
    Args:
        log_level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("docling_ingestion")
    logger.setLevel(log_level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    
    # File handler
    log_file = EXTRACTED_CASES_DIR / "ingestion.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


# ============================================================================
# Metadata Extraction
# ============================================================================

def extract_metadata(text: str, filename: str) -> CaseMetadata:
    """
    Extract structured metadata from legal case text using regex.
    
    Args:
        text: Extracted text content
        filename: Original PDF filename (fallback for case number)
    
    Returns:
        CaseMetadata object with extracted fields
    """
    metadata = CaseMetadata()
    
    # Extract case number (multiple patterns)
    case_patterns = [
        r"Death Reference No[.\s]+(\d+)\s+of\s+(\d+)",
        r"Criminal Appeal No[.\s]+(\d+)\s+of\s+(\d+)",
        r"Civil Appeal No[.\s]+(\d+)\s+of\s+(\d+)",
        r"Criminal Revision No[.\s]+(\d+)\s+of\s+(\d+)",
        r"Civil Revision No[.\s]+(\d+)\s+of\s+(\d+)",
        r"Writ Petition No[.\s]+(\d+)\s+of\s+(\d+)",
        r"Case No[.\s]+(\d+)[/\s]+(\d+)",
    ]
    
    for pattern in case_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            metadata.case_number = match.group(0).strip()
            break
    
    # Fallback: extract from filename
    if not metadata.case_number:
        filename_match = re.search(r"(\d+)_([A-Za-z]+)_", filename)
        if filename_match:
            metadata.case_number = filename_match.group(0).rstrip("_")
    
    # Extract case type
    case_types = [
        "Death Reference",
        "Criminal Appeal",
        "Civil Appeal",
        "Criminal Revision",
        "Civil Revision",
        "Writ Petition",
    ]
    for case_type in case_types:
        if case_type.lower() in text.lower():
            metadata.case_type = case_type
            break
    
    # Extract court
    court_patterns = [
        r"(Supreme Court of Bangladesh[^\n]*)",
        r"(High Court Division[^\n]*)",
        r"(Appellate Division[^\n]*)",
    ]
    for pattern in court_patterns:
        match = re.search(pattern, text)
        if match:
            metadata.court = match.group(1).strip()
            break
    
    # Extract district
    district_match = re.search(r"District:\s*([A-Za-z\s]+)\.?", text)
    if district_match:
        metadata.district = district_match.group(1).strip()
    
    # Extract judges (multiple patterns, limit to first 5)
    judge_patterns = [
        r"Mr\.\s*Justice\s+([A-Za-z\s.]+?)(?:\n|And|$)",
        r"Justice\s+([A-Za-z\s.]+?)(?:\n|And|$)",
        r"Hon'ble\s+Mr\.\s*Justice\s+([A-Za-z\s.]+?)(?:\n|$)",
    ]
    
    judges_found = []
    for pattern in judge_patterns:
        matches = re.findall(pattern, text[:3000])  # Search in first 3000 chars
        if matches:
            judges_found.extend([j.strip() for j in matches])
    
    # Deduplicate and limit
    metadata.judges = list(dict.fromkeys(judges_found))[:5]
    
    # Extract parties (Plaintiff vs Defendant)
    versus_match = re.search(
        r"([A-Za-z\s.]+?)\s+-?\s*Versus\s*-?\s*([A-Za-z\s.]+?)(?:\n|$)",
        text,
        re.IGNORECASE
    )
    if versus_match:
        metadata.parties["plaintiff"] = versus_match.group(1).strip()
        metadata.parties["defendant"] = versus_match.group(2).strip()
    
    # Extract hearing date
    hearing_patterns = [
        r"Heard On:\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4}(?:\s+and\s+[0-9]{2}\.[0-9]{2}\.[0-9]{4})?)",
        r"Date of Hearing:\s*([0-9]{2}[/-][0-9]{2}[/-][0-9]{4})",
    ]
    for pattern in hearing_patterns:
        match = re.search(pattern, text)
        if match:
            metadata.hearing_date = match.group(1).strip()
            break
    
    # Extract judgment date
    judgment_patterns = [
        r"Judgment Delivered On:\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})",
        r"Date of Judgment:\s*([0-9]{2}[/-][0-9]{2}[/-][0-9]{4})",
    ]
    for pattern in judgment_patterns:
        match = re.search(pattern, text)
        if match:
            metadata.judgment_date = match.group(1).strip()
            break
    
    return metadata


# ============================================================================
# PDF Processing
# ============================================================================

def process_pdf(
    pdf_path: Path,
    converter: DocumentConverter,
    logger: logging.Logger
) -> ProcessingResult:
    """
    Process a single PDF file using Docling.
    
    Args:
        pdf_path: Path to the input PDF
        converter: Docling DocumentConverter instance
        logger: Logger instance
    
    Returns:
        ProcessingResult with outputs and status
    """
    result = ProcessingResult(
        input_file=pdf_path.name,
        status="failed"
    )
    
    try:
        logger.info(f"Processing: {pdf_path.name}")
        
        # Convert PDF using Docling
        conversion_result = converter.convert(str(pdf_path))
        
        # Extract markdown text
        markdown_text = conversion_result.document.export_to_markdown()
        
        if not markdown_text or len(markdown_text.strip()) < 50:
            raise ValueError("Insufficient text extracted from PDF")
        
        # Extract metadata
        metadata = extract_metadata(markdown_text, pdf_path.stem)
        
        # Prepare output paths
        base_name = pdf_path.stem
        markdown_path = EXTRACTED_CASES_DIR / f"{base_name}.md"
        json_path = EXTRACTED_CASES_DIR / f"{base_name}.json"
        metadata_path = EXTRACTED_CASES_DIR / f"{base_name}_metadata.json"
        
        # Save Markdown output
        markdown_path.write_text(markdown_text, encoding="utf-8")
        
        # Save JSON output (Docling's structured export)
        json_data = {
            "filename": pdf_path.name,
            "case_number": metadata.case_number,
            "content": markdown_text,
            "metadata": asdict(metadata)
        }
        json_path.write_text(
            json.dumps(json_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        # Save metadata JSON
        metadata_path.write_text(
            json.dumps(asdict(metadata), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        # Calculate statistics
        word_count = len(markdown_text.split())
        char_count = len(markdown_text)
        
        # Update result
        result.status = "success"
        result.markdown_output = str(markdown_path)
        result.json_output = str(json_path)
        result.metadata_output = str(metadata_path)
        result.word_count = word_count
        result.char_count = char_count
        
        logger.info(f"  ✓ {base_name}.md — {word_count:,} words, {char_count:,} chars")
        logger.info(f"    Case: {metadata.case_number or 'Unknown'}")
        logger.info(f"    Court: {metadata.court or 'Not extracted'}")
        logger.info(f"    Judges: {len(metadata.judges)} found")
        
    except Exception as e:
        result.error_message = str(e)
        logger.error(f"  ✗ Failed to process {pdf_path.name}: {e}")
    
    return result


# ============================================================================
# Batch Processing
# ============================================================================

def process_all(
    raw_dir: Path,
    output_dir: Path,
    logger: logging.Logger
) -> Dict:
    """
    Process all PDFs in the raw directory.
    
    Args:
        raw_dir: Directory containing input PDFs
        output_dir: Directory for output files
        logger: Logger instance
    
    Returns:
        Processing summary dictionary
    """
    # Find all PDFs
    pdf_files = sorted(raw_dir.glob("*.pdf"))
    
    if not pdf_files:
        logger.error(f"No PDF files found in {raw_dir}")
        return {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "files": []
        }
    
    logger.info(f"Found {len(pdf_files)} PDF file(s) in {raw_dir}")
    logger.info("=" * 70)
    
    # Initialize Docling converter
    logger.info("Initializing Docling converter...")
    converter = DocumentConverter()
    
    # Process each PDF with progress bar
    results = []
    successful = 0
    failed = 0
    
    for pdf_path in tqdm(pdf_files, desc="Processing PDFs", unit="file"):
        result = process_pdf(pdf_path, converter, logger)
        results.append(asdict(result))
        
        if result.status == "success":
            successful += 1
        else:
            failed += 1
    
    # Prepare summary
    summary = {
        "total": len(pdf_files),
        "successful": successful,
        "failed": failed,
        "files": results,
        "total_words": sum(r["word_count"] for r in results),
        "total_chars": sum(r["char_count"] for r in results)
    }
    
    # Save summary
    summary_path = output_dir / SUMMARY_FILE
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    # Log final summary
    logger.info("=" * 70)
    logger.info("PROCESSING COMPLETE")
    logger.info(f"Total files:     {summary['total']}")
    logger.info(f"Successful:      {summary['successful']}")
    logger.info(f"Failed:          {summary['failed']}")
    logger.info(f"Total words:     {summary['total_words']:,}")
    logger.info(f"Total chars:     {summary['total_chars']:,}")
    logger.info(f"Summary saved:   {summary_path}")
    logger.info("=" * 70)
    
    return summary


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main execution function."""
    # Setup directories
    RAW_CASES_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACTED_CASES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Setup logging
    logger = setup_logging()
    
    logger.info("=" * 70)
    logger.info("Legal Case PDF Ingestion Pipeline (Docling)")
    logger.info("=" * 70)
    logger.info(f"Input directory:  {RAW_CASES_DIR.resolve()}")
    logger.info(f"Output directory: {EXTRACTED_CASES_DIR.resolve()}")
    logger.info("=" * 70)
    
    # Process all PDFs
    summary = process_all(RAW_CASES_DIR, EXTRACTED_CASES_DIR, logger)
    
    # Exit with appropriate code
    exit_code = 0 if summary["failed"] == 0 else 1
    
    if exit_code == 0:
        logger.info("✓ All files processed successfully")
    else:
        logger.warning(f"⚠ {summary['failed']} file(s) failed to process")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())