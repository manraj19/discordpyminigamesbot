"""Pure riddle answer-matching. No discord imports.

Accepts close-but-not-exact answers: case/spacing/punctuation are ignored, a
leading article (a/an/the) is dropped, and the answer may appear as a word
within a longer sentence (so "it's a piano" matches "piano")."""

import re

_ARTICLES = {"a", "an", "the"}


def normalize(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    words = [w for w in text.split() if w]
    if words and words[0] in _ARTICLES:
        words = words[1:]
    return " ".join(words)


def is_correct(guess, answer):
    g = normalize(guess)
    a = normalize(answer)
    if not g or not a:
        return False
    if g == a:
        return True
    if " " in a:  # multi-word answer: accept if it appears within the guess
        return a in g
    return a in g.split()  # single-word answer: must be a whole word in the guess
