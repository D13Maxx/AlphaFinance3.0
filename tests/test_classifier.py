import unittest
from parser.models import Document, Section
from classifier.structural_signals import extract_structural_features

class TestStructuralSignals(unittest.TestCase):
    def test_extract_structural_features(self):
        # Create a mock document with specific headings to trigger features
        # Structure:
        # 1. Executive Summary (Memo)
        # 2. Item 1A. Risk Factors (SEC) - Level 1
        #    2.1 Details (Level 2)
        # 3. Financial Statements (SEC)
        # 4. Net Worth (PFS)
        
        s1 = Section(heading="1. Executive Summary", level=1, start_line=0, end_line=10)
        
        s2_sub = Section(heading="Item 1A. Risk Factors - Details", level=2, start_line=15, end_line=19) # Should NOT trigger item count if nested? Or just by text?
        # Logic says: heading starts with "item ". "Item 1A. Risk Factors" -> Yes.
        # But wait, logic is just text based on current node.
        
        # Let's use strict headings to test normalization
        s2 = Section(heading="Item 1A. Risk Factors", level=1, start_line=11, end_line=30, subsections=[])
        
        # Add a recursive child
        s2.subsections.append(Section(heading="2.1 Nested", level=2, start_line=12, end_line=15))

        s3 = Section(heading="3. Financial Statements", level=1, start_line=31, end_line=40)
        s4 = Section(heading="4. Net Worth Statement", level=1, start_line=41, end_line=50)

        lines = ["line"] * 100 # 100 lines
        
        doc = Document(sections=[s1, s2, s3, s4], lines=lines)
        
        features = extract_structural_features(doc)
        
        # Global
        # Roots: 4. Nested: 1. Total: 5.
        self.assertEqual(features["total_sections"], 5)
        self.assertEqual(features["max_depth"], 2)
        self.assertEqual(features["total_line_count"], 100)
        self.assertEqual(features["avg_section_span"], 20.0) # 100 / 5 = 20
        self.assertTrue(features["is_short_document"]) # 100 < 500
        
        # SEC
        # "Item 1A. Risk Factors" starts with "item " -> count + 1
        self.assertEqual(features["item_section_count"], 1)
        # Normalized "Item 1A. Risk Factors" -> "risk factors". Match.
        self.assertTrue(features["has_risk_factors_section"])
        self.assertTrue(features["has_financial_statements_section"])
        self.assertFalse(features["has_mdna_section"])
        
        # Memo
        self.assertTrue(features["has_executive_summary"]) # "1. Executive Summary"
        self.assertFalse(features["has_exit_strategy"])
        
        # PFS
        self.assertTrue(features["has_net_worth_section"]) # "4. Net Worth Statement"
        self.assertFalse(features["has_assets_section"])

from classifier.content_signals import extract_content_signals

class TestContentSignals(unittest.TestCase):
    def test_extract_content_signals_sec(self):
        # Create a document strong on SEC signals
        # - "Form 10-K" (Strong SEC: 5)
        # - "Item 1A. Risk Factors" (Weak SEC: 1 from "Item ", Medium SEC: 3 from "Risk Factors" -> Total 4?)
        #   Wait, logic: accumulates. 
        #   "Item 1A. Risk Factors":
        #   - Starts with "item " -> +1 SEC
        #   - "risk factors" in text -> +3 SEC
        #   Total for this heading: 4 SEC.
        # - "Management's Discussion" (Medium SEC: 3)
        
        s1 = Section(heading="Form 10-K", level=1, start_line=0, end_line=5)
        s2 = Section(heading="Item 1A. Risk Factors", level=1, start_line=6, end_line=10)
        s3 = Section(heading="7. Management's Discussion", level=1, start_line=11, end_line=20)
        
        # Add some noise
        s4 = Section(heading="Projections", level=1, start_line=21, end_line=30) # +1 Memo
        
        doc = Document(sections=[s1, s2, s3, s4], lines=[])
        
        scores = extract_content_signals(doc)
        
        # Expected scores:
        # SEC: 
        #   s1: "form 10-k" -> +5
        #   s2: "item " -> +1, "risk factors" -> +3 -> +4 total
        #   s3: "management's discussion" -> +3
        #   Total SEC = 5 + 4 + 3 = 12
        
        # Memo:
        #   s4: "projections" -> +1
        #   Total Memo = 1
        
        # PFS: 0
        
        self.assertEqual(scores["SEC_Filing"], 12)
        self.assertEqual(scores["Investment_Memo"], 1)
        self.assertEqual(scores["PFS"], 0)
    
    def test_extract_content_signals_memo(self):
        # Create a document strong on Memo signals
        s1 = Section(heading="Confidential Information Memorandum", level=1, start_line=0, end_line=5) # +5 Memo
        s2 = Section(heading="Investment Highlights", level=1, start_line=6, end_line=10) # +3 Memo
        s3 = Section(heading="Market Opportunity", level=1, start_line=11, end_line=15) # +3 Memo
        
        doc = Document(sections=[s1, s2, s3], lines=[])
        scores = extract_content_signals(doc)
        
        self.assertEqual(scores["Investment_Memo"], 11)
        self.assertEqual(scores["SEC_Filing"], 0)

from classifier.classifier import classify_document

class TestClassifier(unittest.TestCase):
    def test_classify_sec_document(self):
        # Create a document that mimics a 10-K
        # Structural: > 10 sections, MD&A, Risk Factors
        # Content: "Form 10-K", "Risk Factors"
        
        sections = []
        for i in range(15):
            sections.append(Section(heading=f"Item {i}. Data", level=1, start_line=i*10, end_line=i*10+9))
            
        # Specific overrides
        sections[0].heading = "Form 10-K"
        sections[1].heading = "Item 1A. Risk Factors"
        sections[2].heading = "Item 7. Management's Discussion"
        sections[3].heading = "Item 8. Financial Statements"

        doc = Document(sections=sections, lines=["data"] * 200)
        
        result = classify_document(doc)
        self.assertEqual(result["label"], "SEC_Filing")
        self.assertTrue(result["confidence"] > 0.6)
        
    def test_classify_unknown_empty(self):
        # Empty sections, but long enough to avoid "is_short_document" -> PFS trigger
        doc = Document(sections=[], lines=[""] * 600)
        result = classify_document(doc)
        self.assertEqual(result["label"], "Unknown")
        self.assertEqual(result["confidence"], 0.0)

if __name__ == '__main__':
    unittest.main()
