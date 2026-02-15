## Legal Document Ingestion: Handling Bijoy Encoding and Structured Parsing

### Overview

This repository contains experiments on ingesting legal case PDFs that contain both English and Bangla text. A particular challenge in these documents is that Bangla text is often encoded in legacy Bijoy encoding rather than Unicode, which causes parsing errors in standard document processing pipelines.

The purpose of this project was to evaluate different ingestion approaches and understand their behavior when processing multilingual legal documents.

---

### Problem

Many legal documents in Bangladesh:

- Contain English and Bangla in the same PDF
    
- Use Bijoy encoding for Bangla text
    
- Have complex layouts including headings, sections, and citations
    

Standard extraction tools may:

- Corrupt Bangla text
    
- Lose document structure
    
- Fail to preserve reading order
    

This project compares two ingestion approaches to study these issues.

---

### Approach 1: Manual Ingestion Pipeline

The first pipeline extracts text using PDF parsing tools and performs preprocessing steps:

- Text extraction using pdfplumber
    
- Detection of Bangla encoding
    
- Line-level Bijoy to Unicode conversion
    
- Metadata extraction using regex
    
- Text normalization and cleanup
    

Result:

- Bangla text was converted correctly to Unicode
    
- Metadata extraction worked reliably
    
- Some structural formatting from the original document was lost
    

This approach is implemented in:

```
manual_ingestion/
```

---

### Approach 2: Docling-Based Ingestion

The second pipeline uses Docling to perform structured parsing.

Steps:

- Layout-aware PDF parsing
    
- Markdown export
    
- Structured JSON export
    
- Metadata extraction
    

Result:

- Document structure was preserved more accurately
    
- Headings and sections were detected correctly
    
- Bangla text was not always decoded correctly due to Bijoy encoding
    

This approach is implemented in:

```
docling_ingestion/
```

---

### Observations

From these experiments:

1. Layout-aware parsers improve structural quality but do not automatically solve encoding issues.
    
2. Legacy Bangla encodings such as Bijoy require preprocessing or conversion before structured parsing.
    
3. Metadata extraction using simple pattern matching is effective for legal documents with consistent formatting.
    
4. A hybrid pipeline combining encoding normalization with structured parsing may provide the best results.
    

---

### Repository Structure

```
legal-document-ingestion/
│
├── README.md                          # Main project overview
├── .gitignore                         # Exclude data, logs, outputs
│
├── manual_ingestion/                  # Approach 1: Lightweight pipeline
│   ├── README.md                      # Pipeline-specific docs
│   ├── requirements.txt               # pdfplumber, pypdf, bijoy2unicode
│   ├── ingest_legal_cases.py          # Main script
│   └── data/
│       ├── raw_cases/                 # Input PDFs
│       └── extracted_cases/           # Output files
│           ├── *.txt                  # Extracted text
│           ├── *_metadata.json        # Metadata
│           ├── processing_summary.json
│           └── ingestion.log          # Logs
│
├── docling_ingestion/                 # Approach 2: Advanced pipeline
│   ├── README.md                      # Pipeline-specific docs
│   ├── requirements.txt               # docling, tqdm
│   ├── ingest_with_docling.py         # Main script
│   └── data/
│       ├── raw_cases/                 # Input PDFs
│       └── extracted_cases/           # Output files
│           ├── *.md                   # Markdown output
│           ├── *.json                 # Structured JSON
│           ├── *_metadata.json        # Metadata
│           ├── processing_summary.json
│           └── ingestion.log          # Logs
│
└── samples/                           # Example outputs
    ├── sample_output_pdfplumber.txt   # Manual pipeline result
    ├── sample_output_docling.md       # Docling pipeline result
    └── sample_metadata.json           # Sample metadata
```

---

### Current Status

✅ **Manual Pipeline (pdfplumber + bijoy2unicode)**: Fully working
- Successfully processes PDFs with Bijoy Bengali text
- Line-level selective conversion preserves English text
- Tested on sample legal case PDF

⚠️ **Docling Pipeline**: Requires PyTorch installation
- Code is complete and ready to run
- Requires additional ML framework dependencies
- Not tested due to environment constraints

### Running the Pipelines

#### Manual pipeline (Working)

```bash
cd manual_ingestion
pip install -r requirements.txt
python ingest_legal_cases.py
```

#### Docling pipeline (Requires PyTorch)

```bash
cd docling_ingestion
pip install torch  # Install PyTorch first
pip install -r requirements.txt
python ingest_with_docling.py
```

---

### Requirements

Manual pipeline:

- pdfplumber (>=0.10.0)
- pypdf (>=3.17.0)
- bijoy2unicode (>=0.1.0)

Docling pipeline:

- docling (>=2.0.0) — **Requires PyTorch**
- tqdm (>=4.66.0)

**Note:** Docling requires PyTorch/TensorFlow for full functionality. Install with:
```bash
pip install torch  # or tensorflow
pip install docling tqdm
```
    

---

### Limitations

- Tested on a small number of legal documents
    
- Bijoy conversion relies on heuristic detection
    
- Some formatting artifacts remain in extracted text
    

---

### Future Work

Possible improvements include:

- Preprocessing PDFs to normalize encoding before structured parsing
    
- Combining Docling with a Bangla encoding normalization stage
    
- Testing on a larger collection of legal documents
    
- Evaluating impact on downstream retrieval quality
    

---

### Purpose of This Repository

This repository is intended as a learning and experimentation project focused on document ingestion challenges in multilingual legal corpora.
