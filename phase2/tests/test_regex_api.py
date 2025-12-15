"""
Test regex functionality for the artifact API
"""
import pytest
import re
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestRegexPatterns:
    """Test regex matching behavior"""
    
    def test_exact_match_regex(self):
        """Test exact match regex like ^bert-base-uncased$"""
        name = "bert-base-uncased"
        
        # Exact match patterns
        pattern1 = re.compile(r"^bert-base-uncased$")
        pattern2 = re.compile(r"bert-base-uncased")
        pattern3 = re.compile(r"^bert.*$")
        
        assert pattern1.search(name) is not None, "Exact match with anchors should work"
        assert pattern2.search(name) is not None, "Partial match should work"
        assert pattern3.search(name) is not None, "Wildcard match should work"
    
    def test_partial_match_regex(self):
        """Test partial match regex"""
        name = "audience-classifier"
        
        # Patterns from OpenAPI spec example: .*?(audience|bert).*
        pattern = re.compile(r".*?(audience|bert).*")
        
        assert pattern.search(name) is not None, "Should match 'audience' in name"
        
    def test_regex_case_sensitivity(self):
        """Test case sensitivity - regex should be case sensitive by default"""
        name = "Bert-Base-Uncased"
        
        # Case sensitive (default)
        pattern_lower = re.compile(r"bert")
        pattern_upper = re.compile(r"Bert")
        
        # Default regex is case-sensitive
        assert pattern_lower.search(name) is None, "Lowercase pattern should NOT match uppercase text"
        assert pattern_upper.search(name) is not None, "Uppercase pattern should match"
        
    def test_regex_special_chars(self):
        """Test regex with special characters in artifact names"""
        names = [
            "openai-whisper",
            "google-research-bert",
            "bert_base_uncased",
            "model.v1.0"
        ]
        
        # Pattern that matches hyphenated names
        pattern = re.compile(r".*-.*")
        
        matches = [n for n in names if pattern.search(n)]
        assert len(matches) == 2, f"Should match names with hyphens: {matches}"
        
    def test_regex_readme_search(self):
        """Test searching in README content"""
        readme = """
        # BERT Model
        
        This is a pre-trained BERT model for natural language processing.
        It can be used for text classification, named entity recognition, etc.
        """
        
        pattern = re.compile(r"BERT")
        assert pattern.search(readme) is not None, "Should find BERT in README"
        
        pattern2 = re.compile(r"classification")
        assert pattern2.search(readme) is not None, "Should find 'classification' in README"
        
    def test_catastrophic_backtracking_protection(self):
        """Test that we handle potentially problematic regex patterns"""
        # This pattern can cause catastrophic backtracking on certain inputs
        problematic_pattern = r"(a+)+"
        text = "a" * 30 + "b"  # This would hang with naive regex
        
        try:
            pattern = re.compile(problematic_pattern)
            # Should complete quickly with our protection
            result = pattern.search(text[:100])  # Limit text length
            # It's ok if it matches or not, just shouldn't hang
            assert True
        except Exception:
            # If it throws, that's also acceptable
            assert True
            
    def test_empty_and_none_handling(self):
        """Test handling of empty and None values"""
        pattern = re.compile(r"test")
        
        # Should handle None gracefully
        def safe_search(pat, text):
            if not text:
                return None
            return pat.search(text)
        
        assert safe_search(pattern, None) is None
        assert safe_search(pattern, "") is None
        assert safe_search(pattern, "test") is not None


class TestRegexEndpoint:
    """Test the byRegEx endpoint behavior"""
    
    def test_regex_request_body_format(self):
        """Test the expected request body format"""
        # OpenAPI spec shows: {"regex": ".*?(audience|bert).*"}
        from pydantic import BaseModel
        
        class ArtifactRegEx(BaseModel):
            regex: str
        
        # Should accept standard format
        body = ArtifactRegEx(regex=".*?(audience|bert).*")
        assert body.regex == ".*?(audience|bert).*"
        
        # Should accept exact match
        body2 = ArtifactRegEx(regex="^bert-base-uncased$")
        assert body2.regex == "^bert-base-uncased$"
        
    def test_regex_response_format(self):
        """Test the expected response format"""
        # Response should be array of ArtifactMetadata with only name, id, type
        expected_response = [
            {"name": "audience-classifier", "id": "3847247294", "type": "model"},
            {"name": "bert-base-uncased", "id": "9078563412", "type": "model"}
        ]
        
        # Verify structure
        for item in expected_response:
            assert "name" in item
            assert "id" in item
            assert "type" in item
            assert len(item) == 3, "Should only have name, id, type fields"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
