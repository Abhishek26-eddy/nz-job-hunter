import pytest

from app.ai.visa_classifier import VisaClassifier


def test_classify_likely():
    classifier = VisaClassifier()
    result = classifier.classify("We offer visa sponsorship and relocation assistance.")
    assert result == "Likely sponsorship"


def test_classify_not_sponsored():
    classifier = VisaClassifier()
    result = classifier.classify("No visa sponsorship. Must have right to work in the EU.")
    assert result == "Not sponsored"


def test_classify_unknown():
    classifier = VisaClassifier()
    result = classifier.classify("Great opportunity for a senior engineer.")
    assert result == "Possible sponsorship"
