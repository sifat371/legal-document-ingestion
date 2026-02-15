"""
Complete PDF Ingestion with Bijoy to Unicode Conversion
========================================================
Extracts text from legal case PDFs and converts Bijoy Bengali to Unicode.

Installation:
    pip install pdfplumber pypdf bijoy2unicode
"""

from pathlib import Path
import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

# PDF Processing
import pdfplumber
from pypdf import PdfReader

# Bijoy conversion
try:
    from bijoy2unicode.converter import Unicode
    bijoy_converter = Unicode()
    HAS_BIJOY_CONVERTER = True
except ImportError:
    HAS_BIJOY_CONVERTER = False
    print("⚠️  bijoy2unicode not found. Install with: pip install bijoy2unicode")
    print("Bengali text will be preserved as Bijoy encoding.")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CaseMetadata:
    """Metadata extracted from legal case documents"""
    case_number: Optional[str] = None
    case_type: Optional[str] = None
    district: Optional[str] = None
    court: Optional[str] = None
    judges: List[str] = None
    parties: Dict[str, str] = None
    hearing_date: Optional[str] = None
    judgment_date: Optional[str] = None
    citations: List[str] = None
    has_bengali: bool = False
    original_encoding: Optional[str] = None  # 'unicode', 'bijoy', or 'mixed'
    converted_to_unicode: bool = False
    
    def __post_init__(self):
        if self.judges is None:
            self.judges = []
        if self.parties is None:
            self.parties = {}
        if self.citations is None:
            self.citations = []


class BengaliDetector:
    """Detect Bengali text encoding"""
    
    BIJOY_CHARS = set('†‡ˆ‰Š‹ŒŽ''""•–—˜™š›œžŸ ¡¢£¤¥¦§¨©ª«¬­®¯°±²³´µ¶·¸¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïð')
    
    BIJOY_PATTERNS = [
        'Avgvi', 'Av‡', '‡K', 'Zvwi', 'Kwi', 'wQ', 'gvbyl', 'ivÎ',
        'UvKv', 'FY', 'AvBb', 'Av`vjZ', 'Avwg', 'n‡q', 'e‡j'
    ]
    
    @staticmethod
    def detect_unicode_bengali(text: str) -> int:
        """Count Unicode Bengali characters"""
        return sum(1 for c in text if '\u0980' <= c <= '\u09FF')
    
    @staticmethod
    def detect_bijoy_bengali(text: str) -> int:
        """Detect Bijoy encoded Bengali"""
        char_count = sum(1 for c in text if c in BengaliDetector.BIJOY_CHARS)
        pattern_matches = sum(10 for p in BengaliDetector.BIJOY_PATTERNS if p in text)
        return char_count + pattern_matches
    
    @classmethod
    def detect_encoding(cls, text: str) -> Tuple[bool, Optional[str], Dict[str, int]]:
        """
        Returns: (has_bengali, encoding_type, stats)
        """
        unicode_count = cls.detect_unicode_bengali(text)
        bijoy_count = cls.detect_bijoy_bengali(text)
        
        stats = {
            'unicode_chars': unicode_count,
            'bijoy_indicators': bijoy_count,
            'total_chars': len(text)
        }
        
        if unicode_count > 100 and bijoy_count > 50:
            return True, 'mixed', stats
        elif unicode_count > 100:
            return True, 'unicode', stats
        elif bijoy_count > 30:
            return True, 'bijoy', stats
        else:
            return False, None, stats


class LegalCaseExtractor:
    """Extract and process legal case PDFs with Bengali conversion"""
    
    def __init__(self, raw_dir: Path, output_dir: Path, convert_bijoy: bool = True):
        self.raw_dir = Path(raw_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata_dir = self.output_dir / "metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        self.detector = BengaliDetector()
        self.convert_bijoy = convert_bijoy and HAS_BIJOY_CONVERTER
        
        if convert_bijoy and not HAS_BIJOY_CONVERTER:
            logger.warning("Bijoy conversion requested but library not available")
            logger.warning("Install with: pip install bijoy2unicode")
    
    # Bijoy marker characters — present in Bijoy text, absent in plain English
    BIJOY_LINE_MARKERS = set('†‡¨©¯¶ÎïšŒ‰‹Š')
    
    @staticmethod
    def _is_bijoy_line(line: str, threshold: int = 2) -> bool:
        """A line is Bijoy if it has >= threshold Bijoy marker characters."""
        return sum(1 for c in line if c in LegalCaseExtractor.BIJOY_LINE_MARKERS) >= threshold
    
    def extract_text_pdfplumber(self, pdf_path: Path) -> str:
        """Extract text using pdfplumber"""
        try:
            text_parts = []
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"\n--- Page {page_num} ---\n")
                        text_parts.append(page_text)
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"pdfplumber failed for {pdf_path.name}: {e}")
            return ""
    
    def extract_text_pypdf(self, pdf_path: Path) -> str:
        """Extract text using pypdf (fallback)"""
        try:
            text_parts = []
            reader = PdfReader(pdf_path)
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"\n--- Page {page_num} ---\n")
                    text_parts.append(page_text)
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"pypdf failed for {pdf_path.name}: {e}")
            return ""
    
    def extract_text(self, pdf_path: Path) -> str:
        """Extract text with fallback"""
        text = self.extract_text_pdfplumber(pdf_path)
        if not text or len(text.strip()) < 100:
            logger.warning(f"Trying pypdf fallback for {pdf_path.name}")
            text = self.extract_text_pypdf(pdf_path)
        return text
    
    def convert_bengali_to_unicode(self, text: str) -> Tuple[str, bool]:
        """
        Convert only Bijoy-encoded LINES to Unicode.
        English lines are left completely untouched.
        
        Returns: (converted_text, was_converted)
        """
        if not self.convert_bijoy:
            return text, False
        
        converted_lines = []
        bijoy_count = 0
        
        for line in text.split('\n'):
            if self._is_bijoy_line(line):
                try:
                    converted_lines.append(bijoy_converter.convertBijoyToUnicode(line))
                    bijoy_count += 1
                except Exception:
                    converted_lines.append(line)  # keep original on error
            else:
                converted_lines.append(line)  # English — untouched
        
        if bijoy_count > 0:
            logger.info(f"  Converted {bijoy_count} Bijoy line(s) to Unicode (rest kept as English)")
            return '\n'.join(converted_lines), True
        return text, False
    
    def extract_metadata(self, text: str, filename: str) -> CaseMetadata:
        """Extract structured metadata"""
        metadata = CaseMetadata()
        
        # Detect Bengali encoding (before conversion)
        has_bengali, encoding_type, stats = self.detector.detect_encoding(text)
        metadata.has_bengali = has_bengali
        metadata.original_encoding = encoding_type
        
        # Extract case number
        case_num_patterns = [
            r'Death Reference No[.\s]+(\d+)\s+of\s+(\d+)',
            r'Criminal Appeal No[.\s]+(\d+)\s+of\s+(\d+)',
            r'Case No[.\s]+(\d+)[/\s]+(\d+)',
        ]
        
        for pattern in case_num_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata.case_number = match.group(0)
                break
        
        if not metadata.case_number:
            filename_match = re.search(r'(\d+)_([A-Za-z]+)_', filename)
            if filename_match:
                metadata.case_number = filename_match.group(0).rstrip('_')
        
        # Extract case type
        case_types = [
            'Death Reference', 'Criminal Appeal', 'Civil Appeal',
            'Criminal Revision', 'Civil Revision', 'Writ Petition',
        ]
        for case_type in case_types:
            if case_type.lower() in text.lower():
                metadata.case_type = case_type
                break
        
        # Extract district
        district_match = re.search(r'District:\s*([A-Za-z\s]+)\.', text)
        if district_match:
            metadata.district = district_match.group(1).strip()
        
        # Extract court
        court_match = re.search(r'(Supreme Court of Bangladesh[^\n]*)', text)
        if court_match:
            metadata.court = court_match.group(1).strip()
        
        # Extract judges
        judge_patterns = [r'Mr\. Justice ([A-Za-z\s\.]+)', r'Justice ([A-Za-z\s\.]+)']
        for pattern in judge_patterns:
            judges = re.findall(pattern, text[:2000])
            if judges:
                metadata.judges.extend([j.strip() for j in judges])
        metadata.judges = list(dict.fromkeys(metadata.judges))[:5]
        
        # Extract parties
        versus_match = re.search(r'([A-Za-z\s\.]+)\s+-?\s*Versus\s*-?\s*([A-Za-z\s\.]+)', text, re.IGNORECASE)
        if versus_match:
            metadata.parties['plaintiff'] = versus_match.group(1).strip()
            metadata.parties['defendant'] = versus_match.group(2).strip()
        
        # Extract dates
        hearing_match = re.search(r'Heard On:\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4}(?:\s+and\s+[0-9]{2}\.[0-9]{2}\.[0-9]{4})?)', text)
        if hearing_match:
            metadata.hearing_date = hearing_match.group(1)
        
        judgment_match = re.search(r'Judgment Delivered On:\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})', text)
        if judgment_match:
            metadata.judgment_date = judgment_match.group(1)
        
        return metadata
    
    def normalize_text(self, text: str) -> str:
        """Normalize and clean text"""
        if not text:
            return ""
        
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            line = re.sub(r'\s+', ' ', line)
            if len(line) > 1:
                lines.append(line)
        
        merged_lines = []
        buffer = ""
        
        for line in lines:
            if line.startswith("--- Page"):
                if buffer:
                    merged_lines.append(buffer)
                    buffer = ""
                merged_lines.append(line)
                continue
            
            if buffer:
                if re.search(r'[.:;?!।]$', buffer):
                    merged_lines.append(buffer)
                    buffer = line
                else:
                    if buffer.endswith('-') and line and line[0].islower():
                        buffer = buffer[:-1] + line
                    else:
                        buffer = buffer + " " + line
            else:
                buffer = line
        
        if buffer:
            merged_lines.append(buffer)
        
        normalized = "\n\n".join(merged_lines)
        normalized = re.sub(r'\n{3,}', '\n\n', normalized)
        normalized = re.sub(r'\s+([.,;:!?])', r'\1', normalized)
        
        return normalized
    
    def process_pdf(self, pdf_path: Path) -> Tuple[bool, Optional[str]]:
        """Process a single PDF"""
        logger.info(f"Processing: {pdf_path.name}")
        
        try:
            # Extract text
            raw_text = self.extract_text(pdf_path)
            if not raw_text or len(raw_text.strip()) < 100:
                logger.warning(f"Insufficient text from {pdf_path.name}")
                return False, None
            
            # Extract metadata (before conversion)
            metadata = self.extract_metadata(raw_text, pdf_path.stem)
            
            # Convert Bijoy to Unicode if needed
            converted_text, was_converted = self.convert_bengali_to_unicode(raw_text)
            metadata.converted_to_unicode = was_converted
            
            # Normalize
            clean_text = self.normalize_text(converted_text)
            if not clean_text.strip():
                logger.warning(f"No text after normalization for {pdf_path.name}")
                return False, None
            
            # Save text
            text_output_path = self.output_dir / f"{pdf_path.stem}.txt"
            text_output_path.write_text(clean_text, encoding="utf-8")
            
            # Save metadata
            metadata_output_path = self.metadata_dir / f"{pdf_path.stem}_metadata.json"
            metadata_output_path.write_text(
                json.dumps(asdict(metadata), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            
            # Log statistics
            word_count = len(clean_text.split())
            char_count = len(clean_text)
            
            bengali_info = ""
            if metadata.has_bengali:
                conversion_status = " → Unicode" if was_converted else " (preserved)"
                bengali_info = f" [Bengali: {metadata.original_encoding}{conversion_status}]"
            
            logger.info(f"✓ Saved: {text_output_path.name}")
            logger.info(f"  Stats: {word_count:,} words, {char_count:,} characters{bengali_info}")
            logger.info(f"  Metadata: Case {metadata.case_number or 'Unknown'}")
            
            return True, str(text_output_path)
        
        except Exception as e:
            logger.error(f"Error processing {pdf_path.name}: {e}", exc_info=True)
            return False, None
    
    def process_all(self) -> Dict:
        """Process all PDFs"""
        pdf_files = list(self.raw_dir.glob("*.pdf"))
        
        if not pdf_files:
            logger.error(f"No PDF files in {self.raw_dir}")
            return {"total": 0, "successful": 0, "failed": 0, "files": []}
        
        logger.info(f"Found {len(pdf_files)} PDF files")
        
        results = {
            "total": len(pdf_files),
            "successful": 0,
            "failed": 0,
            "files": [],
            "bengali_stats": {
                "unicode": 0,
                "bijoy": 0,
                "mixed": 0,
                "none": 0,
                "converted": 0
            }
        }
        
        for pdf_path in pdf_files:
            success, output_path = self.process_pdf(pdf_path)
            
            if success:
                results["successful"] += 1
                
                # Get Bengali stats
                metadata_file = self.metadata_dir / f"{pdf_path.stem}_metadata.json"
                if metadata_file.exists():
                    metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
                    encoding = metadata.get('original_encoding')
                    if encoding:
                        results["bengali_stats"][encoding] += 1
                        if metadata.get('converted_to_unicode'):
                            results["bengali_stats"]["converted"] += 1
                    else:
                        results["bengali_stats"]["none"] += 1
                
                results["files"].append({
                    "input": str(pdf_path),
                    "output": output_path,
                    "status": "success"
                })
            else:
                results["failed"] += 1
                results["files"].append({
                    "input": str(pdf_path),
                    "output": None,
                    "status": "failed"
                })
        
        # Save summary
        summary_path = self.output_dir / "processing_summary.json"
        summary_path.write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        logger.info("\n" + "="*60)
        logger.info(f"Processing Complete!")
        logger.info(f"Total: {results['total']}, Success: {results['successful']}, Failed: {results['failed']}")
        logger.info(f"\nBengali Detection:")
        logger.info(f"  Unicode: {results['bengali_stats']['unicode']}")
        logger.info(f"  Bijoy: {results['bengali_stats']['bijoy']}")
        logger.info(f"  Mixed: {results['bengali_stats']['mixed']}")
        logger.info(f"  None: {results['bengali_stats']['none']}")
        logger.info(f"  Converted to Unicode: {results['bengali_stats']['converted']}")
        logger.info("="*60)
        
        return results


def main():
    """Main execution"""
    RAW_DIR = Path("data/raw_cases")
    OUTPUT_DIR = Path("data/extracted_cases")
    
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize with Bijoy conversion enabled
    extractor = LegalCaseExtractor(RAW_DIR, OUTPUT_DIR, convert_bijoy=True)
    
    results = extractor.process_all()
    
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    exit(main())