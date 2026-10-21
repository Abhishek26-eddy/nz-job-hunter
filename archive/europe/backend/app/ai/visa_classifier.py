import re


class VisaClassifier:
    POSITIVE_KEYWORDS = [
        "visa sponsorship",
        "sponsorship",
        "relocation package",
        "relocation assistance",
        "relocation support",
        "blue card",
        "eu blue card",
        "work permit",
        "international applicants",
        "global talent",
        "talent visa",
        "sponsored visa",
        "will sponsor",
        "can sponsor",
        "visa assistance",
        "relocation",
        "move to",
        "relocate",
        "we sponsor",
    ]

    NEGATIVE_KEYWORDS = [
        "no sponsorship",
        "we do not sponsor",
        "no visa sponsorship",
        "must have the right to work",
        "must be eligible to work",
        "must have valid work authorization",
        "only eu citizens",
        "only european citizens",
        "requires eu work permit",
    ]

    def classify(self, text: str | None) -> str:
        if not text:
            return "Unknown"
        lowered = text.lower()
        negative_hits = [kw for kw in self.NEGATIVE_KEYWORDS if kw in lowered]
        if negative_hits:
            return "Not sponsored"
        positive_hits = [kw for kw in self.POSITIVE_KEYWORDS if kw in lowered]
        if positive_hits:
            return "Likely sponsorship"
        return "Possible sponsorship"
