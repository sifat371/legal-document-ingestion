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
manual_ingestion/
    ingest_legal_cases.py

docling_ingestion/
    ingest_with_docling.py

samples/
    example outputs from both pipelines
```

---

### Running the Pipelines

#### Manual pipeline

```
cd manual_ingestion
pip install -r requirements.txt
python ingest_legal_cases.py
```

#### Docling pipeline

```
cd docling_ingestion
pip install -r requirements.txt
python ingest_with_docling.py
```

---

### Requirements

Manual pipeline:

- pdfplumber
    
- pypdf
    
- bijoy2unicode
    

Docling pipeline:

- docling
    
- tqdm
    

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
