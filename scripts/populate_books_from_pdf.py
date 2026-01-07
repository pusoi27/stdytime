#!/usr/bin/env python3
"""
Extract books from RRL chart PDF and populate the database.
Usage: python populate_books_from_pdf.py
"""

import pdfplumber
import sqlite3
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.database import DB_PATH

# Levels in order as they appear in the PDF
# Page 1: 7A, 6A, 5A, 4A, 3A
# Page 3: 2A, A, B, C, D, E, F
# Page 4: G, H, I, J, K, L
LEVELS_PAGE1 = ["7A", "6A", "5A", "4A", "3A"]
LEVELS_PAGE3 = ["2A", "A", "B", "C", "D", "E", "F"]
LEVELS_PAGE4 = ["G", "H", "I", "J", "K", "L"]
ALL_LEVELS = LEVELS_PAGE1 + LEVELS_PAGE3 + LEVELS_PAGE4

def clean_text(text):
    """Clean up extracted text (remove extra newlines, fix encoding issues)."""
    if not text:
        return ""
    text = text.replace('\u00ad', '')  # Remove soft hyphens
    text = text.replace('  ', ' ').strip()
    return text

def parse_book_entry(entry_str):
    """
    Parse a book entry string into title, author, publisher.
    Format: "Title\nAuthor" or "Title\nAuthor\nPublisher"
    """
    lines = [l.strip() for l in entry_str.split('\n') if l.strip()]
    
    if len(lines) == 0:
        return None, None, None
    elif len(lines) == 1:
        return clean_text(lines[0]), None, None
    elif len(lines) == 2:
        return clean_text(lines[0]), clean_text(lines[1]), None
    else:
        # Multiple lines: title, author, publisher
        title = clean_text(lines[0])
        author = clean_text(lines[1])
        publisher = clean_text('\n'.join(lines[2:]))
        return title, author, publisher

def extract_books_from_pdf(pdf_path):
    """Extract all books from all PDF pages and return as dict: {level: [books]}"""
    books_by_level = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        # Page 1 (index 0): 7A, 6A, 5A, 4A, 3A
        tables_p1 = pdf.pages[0].extract_tables()
        page1_levels = LEVELS_PAGE1
        
        # Page 3 (index 2): 2A, A, B, C, D, E, F
        tables_p3 = pdf.pages[2].extract_tables()
        page3_levels = LEVELS_PAGE3
        
        # Page 4 (index 3): G, H, I, J, K, L
        tables_p4 = pdf.pages[3].extract_tables()
        page4_levels = LEVELS_PAGE4
        
        # Process page 1
        for level_idx, table in enumerate(tables_p1[:len(page1_levels)]):
            level = page1_levels[level_idx]
            books_by_level[level] = _extract_books_from_table(table, level)
        
        # Process page 3
        for level_idx, table in enumerate(tables_p3[:len(page3_levels)]):
            level = page3_levels[level_idx]
            books_by_level[level] = _extract_books_from_table(table, level)
        
        # Process page 4
        for level_idx, table in enumerate(tables_p4[:len(page4_levels)]):
            level = page4_levels[level_idx]
            books_by_level[level] = _extract_books_from_table(table, level)
    
    return books_by_level

def _extract_books_from_table(table, level):
    """Extract books from a single table."""
    books = []
    
    for row in table:
        if not row or len(row) < 3:
            continue
        
        try:
            num = row[0].strip()
            entry = row[1]
            publisher_cell = row[2] if len(row) > 2 else ""
            
            # Parse the entry
            title, author, pub_from_entry = parse_book_entry(entry)
            
            if not title:
                continue
            
            # If publisher wasn't fully extracted from entry, use publisher cell
            if not pub_from_entry and publisher_cell:
                pub_from_entry = clean_text(publisher_cell)
            
            books.append({
                'title': title,
                'author': author or "Unknown",
                'publisher': pub_from_entry or "Unknown",
                'reading_level': level,
                'available': 1
            })
            
        except Exception as e:
            continue
    
    return books

def populate_database(books_by_level):
    """Insert or update books in the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    total_inserted = 0
    total_updated = 0
    
    for level, books in books_by_level.items():
        for book in books:
            # Check if book already exists
            c.execute(
                "SELECT id FROM books WHERE title=? AND author=?",
                (book['title'], book['author'])
            )
            existing = c.fetchone()
            
            if existing:
                # Update existing book
                c.execute("""
                    UPDATE books 
                    SET publisher=?, reading_level=?, available=?
                    WHERE id=?
                """, (book['publisher'], book['reading_level'], book['available'], existing[0]))
                total_updated += 1
            else:
                # Insert new book
                c.execute("""
                    INSERT INTO books 
                    (title, author, publisher, reading_level, available, copies)
                    VALUES (?, ?, ?, ?, ?, 1)
                """, (book['title'], book['author'], book['publisher'], book['reading_level'], book['available']))
                total_inserted += 1
    
    conn.commit()
    conn.close()
    
    return total_inserted, total_updated

def main():
    pdf_path = r"C:\Users\octav\Downloads\New RRL chart 7A-L_2024.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found at {pdf_path}")
        return
    
    print(f"Reading PDF: {pdf_path}")
    books_by_level = extract_books_from_pdf(pdf_path)
    
    # Display extracted data
    total_books = 0
    for level in ALL_LEVELS:
        count = len(books_by_level.get(level, []))
        print(f"Level {level}: {count} books")
        total_books += count
        
        # Show first 2 books as sample
        for book in books_by_level.get(level, [])[:2]:
            print(f"  - {book['title']} by {book['author']}")
    
    print(f"\nTotal books extracted: {total_books}")
    
    # Populate database
    print("\nPopulating database...")
    inserted, updated = populate_database(books_by_level)
    
    print(f"\nResults:")
    print(f"  Inserted: {inserted} new books")
    print(f"  Updated: {updated} existing books")
    print(f"  Total: {inserted + updated} books")

if __name__ == "__main__":
    main()
