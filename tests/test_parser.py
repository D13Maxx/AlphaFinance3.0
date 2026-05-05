import unittest
from parser.parser import parse_document
from parser.models import Document, Section

class TestParser(unittest.TestCase):
    
    def test_numbered_structure(self):
        text = """1. Introduction
This is intro text.
1.1 Details
Detail text.
2. Conclusion
Final thoughts."""
        doc = parse_document(text)
        
        # Check root sections
        self.assertEqual(len(doc.sections), 2)
        self.assertEqual(doc.sections[0].heading, "1. Introduction")
        self.assertEqual(doc.sections[1].heading, "2. Conclusion")
        
        # Check subsections
        intro = doc.sections[0]
        self.assertEqual(len(intro.subsections), 1)
        self.assertEqual(intro.subsections[0].heading, "1.1 Details")
        
        # Check lines assignment
        # Intro starts at 0. Ends at 3?
        # 0: 1. Heading
        # 1: text
        # 2: 1.1 Heading
        # 3: text
        # 4: 2. Heading
        # So intro should end at 3 (before line 4).
        # Wait, Intro contains Heading 1, line 1.
        # Subsection 1.1 starts at 2.
        # So Intro main body is 0-1?
        # The Section object *covers* the subsection lines too (hierarchical).
        # So Intro (L1) spans from 0 until 4 (start of 2. Conclusion).
        # So Intro.end_line should be 3.
        self.assertEqual(intro.start_line, 0)
        self.assertEqual(intro.end_line, 3)
        
        # Subsection 1.1
        # Starts 2. Ends 3.
        self.assertEqual(intro.subsections[0].start_line, 2)
        self.assertEqual(intro.subsections[0].end_line, 3)

    def test_memo_structure(self):
        text = """Start of file.
INTRODUCTION
Some text here.
BACKGROUND
More text here.
Item 1.
First item.
Item 2.
Second item."""
        doc = parse_document(text)
        
        # Structure expects:
        # Line 0: "Start of file." (Orphan? Or part of implicit preamble?)
        # Since heading detection starts at line 1 "INTRODUCTION", 
        # lines before line 1 are ignored or attached to nothing?
        # The code creates root sections starting from first heading.
        # So "Start of file." is effectively skipped in the section list but present in lines.
        
        self.assertTrue(len(doc.sections) >= 2)
        # Check standard headers
        headings = [s.heading for s in doc.sections]
        self.assertIn("INTRODUCTION", headings)
        self.assertIn("BACKGROUND", headings)
        self.assertIn("Item 1.", headings)
        
        # Check hierarchy
        # Item X. is Priority A, level 1.
        # INTRODUCTION is Priority B/C, usually level 1?
        # If all are level 1, they are siblings.

    def test_no_heading_fallback(self):
        text = """Just a plain document.
With no headings.
Multiple lines."""
        doc = parse_document(text)
        
        self.assertEqual(len(doc.sections), 1)
        self.assertEqual(doc.sections[0].heading, "Document")
        self.assertEqual(doc.sections[0].level, 1)
        self.assertEqual(doc.sections[0].start_line, 0)
        self.assertEqual(doc.sections[0].end_line, 2)

if __name__ == '__main__':
    unittest.main()
