# PDF Processing Dependencies Installation Guide

## Quick Install (Recommended)

### Option 1: Text-based PDFs (Fast, Lightweight)
```bash
pip install pdfplumber pymupdf
```

### Option 2: Scanned PDFs (Requires OCR)
```bash
# Install PaddleOCR (Best for Chinese)
pip install paddlepaddle paddleocr

# Or install Tesseract OCR
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
# Mac: brew install tesseract
# Linux: sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract
```

## Full Installation (All Features)
```bash
pip install pdfplumber pymupdf paddlepaddle paddleocr pytesseract pillow
```

## Usage

### Step 1: Process PDF Books
```bash
python scripts/process_pdf_books.py
```

This will:
- Detect available OCR methods
- Extract text from all 4 sales books
- Identify cases, dialogues, and techniques
- Create structured semantic chunks
- Save to `storage/processed_data/books/`

Expected output:
- 200-500 new semantic chunks
- Organized by book type
- Ready for integration

### Step 2: Integrate with Existing Knowledge Base
```bash
python scripts/integrate_book_knowledge.py
```

This will:
- Load existing 375 chunks
- Load new book chunks
- Deduplicate and validate
- Merge into single knowledge base
- Create backup before merging
- Update `semantic_chunks.json`

Expected result:
- 600-800 total chunks (60-100% growth)
- Backup saved to `storage/processed_data/backups/`

### Step 3: Rebuild Vector Store
```bash
python scripts/fix_semantic_search.py
```

This will:
- Reload expanded knowledge base
- Regenerate embeddings for all chunks
- Update vector store in memory

### Step 4: Test Agent Integration
```bash
python scripts/test_agent_integration.py
```

Verify that agents can access expanded knowledge.

## Troubleshooting

### Issue: "No OCR libraries available"
**Solution**: Install at least one OCR library:
```bash
pip install pdfplumber  # Easiest, works for most PDFs
```

### Issue: "Extraction failed" for scanned PDFs
**Solution**: Install PaddleOCR for better Chinese OCR:
```bash
pip install paddlepaddle paddleocr
```

### Issue: Out of memory during OCR
**Solution**: Process books one at a time by modifying the script:
```python
# In process_pdf_books.py, comment out books you don't want to process yet
self.books = [
    self.books[0]  # Process only first book
]
```

### Issue: Slow OCR processing
**Expected**: PaddleOCR processes ~1-2 pages per second
- 《绝对成交》(~200 pages) = ~3-5 minutes
- Total for all 4 books = ~15-30 minutes

**Tip**: Run overnight or during lunch break

## Performance Expectations

### Processing Time
| Book | Size | Pages (est) | Time (pdfplumber) | Time (OCR) |
|------|------|-------------|-------------------|------------|
| 《绝对成交》 | 46MB | ~200 | 30s | 5-10min |
| 销售心态&技巧 | 11MB | ~80 | 15s | 2-4min |
| 销售技巧培训 | 7.5MB | ~60 | 10s | 2-3min |
| 招商银行教程 | 6.6MB | ~50 | 10s | 2-3min |
| **Total** | 71.1MB | ~390 | **~1min** | **~15min** |

### Output Quality
- **Text-based PDFs**: 95-99% accuracy
- **Scanned PDFs**: 85-95% accuracy (with PaddleOCR)
- **Expected chunks**: 200-500 high-quality semantic blocks

## Next Steps After Integration

1. **Test Query Quality**
   ```bash
   python scripts/test_semantic_quality.py
   ```

2. **Monitor Agent Performance**
   - Check if agents provide more detailed answers
   - Verify champion case diversity increased
   - Confirm technique coverage expanded

3. **User Acceptance Testing**
   - Deploy to staging environment
   - Collect user feedback on answer quality
   - Measure improvement in user satisfaction

## Cost-Benefit Analysis

### Investment
- **Time**: 1-2 hours (mostly automated)
- **Compute**: Minimal (CPU-based OCR)
- **Storage**: +50-100MB (semantic chunks + vectors)

### Return
- **Knowledge Coverage**: +60-100% (375 → 600-800 chunks)
- **Answer Quality**: Significantly improved
- **Competitive Advantage**: Professional sales knowledge base
- **User Satisfaction**: Higher quality AI responses

## Support

If you encounter issues:
1. Check the error message in console output
2. Verify PDF files exist in `storage/source_documents/`
3. Ensure at least one OCR library is installed
4. Review processing logs in `storage/processed_data/books/`

For technical support, refer to:
- PaddleOCR docs: https://github.com/PaddlePaddle/PaddleOCR
- pdfplumber docs: https://github.com/jsvine/pdfplumber
- PyMuPDF docs: https://pymupdf.readthedocs.io/
