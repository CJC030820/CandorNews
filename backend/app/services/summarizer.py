from typing import List, Dict
import logging
import re

logger = logging.getLogger(__name__)

class SummarizerService:
    def __init__(self, max_sentences: int = 4):
        self.max_sentences = max_sentences

    # Words that end with a full stop but do not end a sentence.
    ABBREVIATIONS = {
        "dr", "mr", "mrs", "ms", "prof", "sr", "jr", "st", "no", "vs", "etc", "inc", "ltd", "co", "corp",
        "bhd", "sdn", "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
        "gen", "lt", "col", "capt", "sgt", "gov", "sen", "rep", "hon", "dept", "approx", "est", "e.g", "i.e",
    }
    # A sentence ends at . ! or ? (optionally followed by quotes/brackets) and then whitespace.
    CLOSERS = "\"'’”)]"
    _END = re.compile(r"[.!?]+[\"'’”)\]]*(?=\s|$)")

    def _sentences(self, text: str) -> List[str]:
        """Split into sentences, keeping decimals (3.5), initials (U.S.) and
        common abbreviations (Dr., Bhd.) inside their sentence."""
        sentences, start = [], 0
        for match in self._END.finditer(text):
            end = match.end()
            before = text[start:match.start()].split()
            word = before[-1].lower().rstrip(".") if before else ""
            nxt = text[end:].lstrip()[:1]
            is_abbrev = match.group().startswith(".") and (
                word in self.ABBREVIATIONS or (len(word) == 1 and word.isalpha()) or "." in word)
            if is_abbrev or (nxt and nxt.islower()):
                continue
            sentence = text[start:end].strip()
            if any(ch.isalnum() for ch in sentence):
                sentences.append(sentence)
            start = end
        rest = text[start:].strip()
        if any(ch.isalnum() for ch in rest):
            sentences.append(rest)
        return sentences

    def summarize(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text).strip()
        summary = " ".join(self._sentences(text)[:self.max_sentences])
        if summary and summary[-1] not in ".!?" + self.CLOSERS:
            summary += "."
        return summary

    def summarize_article(self, article: Dict) -> str:
        # Use description if available, otherwise content excerpt
        description = article.get("description", "")
        content = article.get("content_excerpt", "") or article.get("content", "")

        if description:
            return self.summarize(description)
        elif content:
            return self.summarize(content)
        else:
            return "No summary available."