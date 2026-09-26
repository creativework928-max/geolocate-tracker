from __future__ import annotations

import io
import math
import re
import statistics
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

import streamlit as st


# ============================================================================
# APPLICATION METADATA
# ============================================================================

APP_NAME = "EssayScore AI"
APP_VERSION = "1.0.0"

MAX_ESSAY_CHARACTERS = 50_000
MIN_ESSAY_CHARACTERS = 30

DEFAULT_MIN_WORDS = 150
DEFAULT_MAX_WORDS = 1_000

SCORE_MAX = 100


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title=f"{APP_NAME} — Automated Essay Scoring",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown(
    """
<style>
    /* ---------------------------------------------------------------------
       Global
    --------------------------------------------------------------------- */

    :root {
        --bg: #07111f;
        --bg-soft: #0a1728;
        --surface: #0f1d30;
        --surface-2: #13253b;
        --border: rgba(148, 163, 184, 0.16);
        --text: #f8fafc;
        --muted: #94a3b8;
        --primary: #38bdf8;
        --primary-dark: #0284c7;
        --success: #34d399;
        --warning: #fbbf24;
        --danger: #fb7185;
        --purple: #a78bfa;
    }

    .stApp {
        background:
            radial-gradient(
                circle at 15% 0%,
                rgba(56, 189, 248, 0.09),
                transparent 30%
            ),
            radial-gradient(
                circle at 90% 10%,
                rgba(167, 139, 250, 0.08),
                transparent 28%
            ),
            var(--bg);
        color: var(--text);
    }

    .main .block-container {
        max-width: 1450px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    /* ---------------------------------------------------------------------
       Header
    --------------------------------------------------------------------- */

    .hero {
        background:
            linear-gradient(
                135deg,
                rgba(15, 29, 48, 0.98),
                rgba(10, 23, 40, 0.98)
            );
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 2rem 2.2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.24);
    }

    .brand-row {
        display: flex;
        align-items: center;
        gap: 14px;
    }

    .brand-icon {
        width: 52px;
        height: 52px;
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        background:
            linear-gradient(
                135deg,
                var(--primary),
                var(--primary-dark)
            );
        color: white;
        font-size: 26px;
        box-shadow: 0 10px 30px rgba(14, 165, 233, 0.24);
    }

    .hero h1 {
        color: var(--text);
        font-size: 2.15rem;
        margin: 0;
        font-weight: 800;
        letter-spacing: -0.04em;
    }

    .hero-subtitle {
        color: var(--muted);
        margin-top: 0.55rem;
        font-size: 1rem;
        line-height: 1.6;
        max-width: 850px;
    }

    .live-badge {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        margin-top: 1rem;
        padding: 6px 11px;
        border-radius: 999px;
        color: #a7f3d0;
        background: rgba(52, 211, 153, 0.09);
        border: 1px solid rgba(52, 211, 153, 0.20);
        font-size: 0.78rem;
        font-weight: 700;
    }

    .live-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--success);
        box-shadow: 0 0 10px rgba(52, 211, 153, 0.8);
    }

    /* ---------------------------------------------------------------------
       Cards
    --------------------------------------------------------------------- */

    .card {
        background: rgba(15, 29, 48, 0.94);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.16);
    }

    .section-title {
        color: var(--text);
        font-size: 1.05rem;
        font-weight: 750;
        margin-bottom: 0.3rem;
    }

    .section-description {
        color: var(--muted);
        font-size: 0.84rem;
        margin-bottom: 1rem;
    }

    /* ---------------------------------------------------------------------
       Metrics
    --------------------------------------------------------------------- */

    .metric-card {
        background: linear-gradient(
            145deg,
            rgba(19, 37, 59, 0.96),
            rgba(13, 27, 46, 0.96)
        );
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1rem;
        min-height: 110px;
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
    }

    .metric-value {
        color: var(--text);
        font-size: 1.7rem;
        font-weight: 800;
        margin-top: 0.35rem;
    }

    .metric-help {
        color: var(--muted);
        font-size: 0.75rem;
        margin-top: 0.2rem;
    }

    /* ---------------------------------------------------------------------
       Score
    --------------------------------------------------------------------- */

    .score-panel {
        text-align: center;
        background:
            radial-gradient(
                circle at 50% 15%,
                rgba(56, 189, 248, 0.12),
                transparent 45%
            ),
            rgba(15, 29, 48, 0.96);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 1.6rem;
    }

    .score-number {
        font-size: 4.8rem;
        line-height: 1;
        font-weight: 900;
        letter-spacing: -0.07em;
    }

    .score-denominator {
        color: var(--muted);
        font-size: 1rem;
    }

    .score-label {
        margin-top: 0.7rem;
        color: var(--text);
        font-weight: 750;
        font-size: 1.1rem;
    }

    .score-description {
        color: var(--muted);
        font-size: 0.82rem;
        margin-top: 0.4rem;
    }

    /* ---------------------------------------------------------------------
       Findings
    --------------------------------------------------------------------- */

    .finding {
        padding: 0.85rem 1rem;
        border-radius: 12px;
        margin-bottom: 0.65rem;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.02);
    }

    .finding-title {
        color: var(--text);
        font-weight: 700;
        font-size: 0.88rem;
    }

    .finding-body {
        color: var(--muted);
        font-size: 0.8rem;
        line-height: 1.55;
        margin-top: 0.25rem;
    }

    .finding-success {
        border-left: 3px solid var(--success);
    }

    .finding-warning {
        border-left: 3px solid var(--warning);
    }

    .finding-danger {
        border-left: 3px solid var(--danger);
    }

    .finding-info {
        border-left: 3px solid var(--primary);
    }

    /* ---------------------------------------------------------------------
       Footer
    --------------------------------------------------------------------- */

    .footer {
        margin-top: 3rem;
        padding-top: 1.3rem;
        border-top: 1px solid var(--border);
        color: var(--muted);
        font-size: 0.76rem;
        line-height: 1.7;
        text-align: center;
    }

    /* ---------------------------------------------------------------------
       Streamlit overrides
    --------------------------------------------------------------------- */

    div[data-testid="stTextArea"] textarea {
        background: #091729 !important;
        color: #f8fafc !important;
        border: 1px solid rgba(148, 163, 184, 0.20) !important;
        border-radius: 14px !important;
        line-height: 1.75 !important;
        font-size: 0.96rem !important;
    }

    div[data-testid="stTextArea"] textarea:focus {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.28) !important;
    }

    div.stButton > button {
        border-radius: 11px;
        min-height: 42px;
        font-weight: 700;
        transition: all 0.2s ease;
    }

    div.stButton > button:hover {
        transform: translateY(-1px);
    }

    div[data-testid="stMetric"] {
        background: rgba(15, 29, 48, 0.94);
        border: 1px solid var(--border);
        padding: 0.8rem;
        border-radius: 14px;
    }

    /* ---------------------------------------------------------------------
       Mobile
    --------------------------------------------------------------------- */

    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem 0.8rem 3rem;
        }

        .hero {
            padding: 1.35rem;
            border-radius: 18px;
        }

        .hero h1 {
            font-size: 1.65rem;
        }

        .score-number {
            font-size: 3.7rem;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class EssayStatistics:
    words: int
    characters: int
    characters_no_spaces: int
    sentences: int
    paragraphs: int
    average_word_length: float
    average_sentence_length: float
    unique_words: int
    lexical_diversity: float
    long_words: int
    transition_words: int


@dataclass
class CriterionScore:
    name: str
    score: float
    weight: float
    description: str


@dataclass
class EssayResult:
    overall_score: float
    grade: str
    statistics: EssayStatistics
    criteria: list[CriterionScore]
    strengths: list[str]
    improvements: list[str]
    warnings: list[str]
    suggestions: list[str]
    generated_at: str


# ============================================================================
# TEXT PROCESSING
# ============================================================================

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "hers",
    "him",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "may",
    "me",
    "might",
    "more",
    "most",
    "my",
    "no",
    "not",
    "of",
    "on",
    "or",
    "our",
    "ours",
    "she",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "to",
    "too",
    "under",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
    "yours",
}


TRANSITION_WORDS = {
    "however",
    "therefore",
    "moreover",
    "furthermore",
    "additionally",
    "consequently",
    "nevertheless",
    "although",
    "because",
    "thus",
    "meanwhile",
    "similarly",
    "likewise",
    "firstly",
    "secondly",
    "finally",
    "overall",
    "for example",
    "for instance",
    "in contrast",
    "on the other hand",
    "as a result",
    "in addition",
    "in conclusion",
}


ACADEMIC_WORDS = {
    "analysis",
    "argument",
    "evidence",
    "significant",
    "demonstrates",
    "indicates",
    "suggests",
    "perspective",
    "consequence",
    "factor",
    "approach",
    "principle",
    "impact",
    "research",
    "context",
    "concept",
    "theory",
    "evaluate",
    "evaluation",
    "compare",
    "comparison",
    "contrast",
    "however",
    "therefore",
    "moreover",
    "furthermore",
    "specifically",
    "particularly",
    "effectively",
    "ultimately",
}


COMMON_SPELLING_ERRORS = {
    "recieve": "receive",
    "seperate": "separate",
    "definately": "definitely",
    "occured": "occurred",
    "accomodate": "accommodate",
    "begining": "beginning",
    "beleive": "believe",
    "enviroment": "environment",
    "goverment": "government",
    "neccessary": "necessary",
    "succesful": "successful",
    "untill": "until",
    "wich": "which",
    "thier": "their",
    "teh": "the",
    "becuase": "because",
    "adress": "address",
    "arguement": "argument",
    "responsibile": "responsible",
    "occassion": "occasion",
    "tommorow": "tomorrow",
    "writting": "writing",
    "usefull": "useful",
}


def normalize_text(text: str) -> str:
    """Normalize whitespace without destroying paragraph structure."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def tokenize_words(text: str) -> list[str]:
    """Return normalized alphabetic word tokens."""
    return re.findall(r"\b[a-zA-Z]+(?:'[a-zA-Z]+)?\b", text.lower())


def split_sentences(text: str) -> list[str]:
    """
    Lightweight sentence segmentation.

    This deliberately avoids pretending to be a full linguistic parser.
    """
    if not text.strip():
        return []

    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def split_paragraphs(text: str) -> list[str]:
    return [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]


def calculate_transition_count(text: str) -> int:
    lower = text.lower()
    count = 0

    for transition in TRANSITION_WORDS:
        if " " in transition:
            count += len(re.findall(rf"\b{re.escape(transition)}\b", lower))
        else:
            count += len(re.findall(rf"\b{re.escape(transition)}\b", lower))

    return count


def calculate_statistics(text: str) -> EssayStatistics:
    words = tokenize_words(text)
    sentences = split_sentences(text)
    paragraphs = split_paragraphs(text)

    word_count = len(words)
    sentence_count = len(sentences)

    unique_words = len(
        {
            word
            for word in words
            if word not in STOPWORDS
        }
    )

    content_words = [
        word
        for word in words
        if word not in STOPWORDS
    ]

    lexical_diversity = (
        unique_words / len(content_words)
        if content_words
        else 0.0
    )

    average_word_length = (
        statistics.mean(len(word) for word in words)
        if words
        else 0.0
    )

    average_sentence_length = (
        word_count / sentence_count
        if sentence_count
        else 0.0
    )

    long_words = sum(1 for word in words if len(word) >= 8)

    return EssayStatistics(
        words=word_count,
        characters=len(text),
        characters_no_spaces=len(re.sub(r"\s", "", text)),
        sentences=sentence_count,
        paragraphs=len(paragraphs),
        average_word_length=round(average_word_length, 2),
        average_sentence_length=round(average_sentence_length, 2),
        unique_words=unique_words,
        lexical_diversity=round(lexical_diversity, 3),
        long_words=long_words,
        transition_words=calculate_transition_count(text),
    )


# ============================================================================
# QUALITY ANALYSIS
# ============================================================================

def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def score_length(stats: EssayStatistics) -> float:
    """
    Score essay length.

    Longer is not automatically better. The score rewards an adequate
    amount of developed writing and gently penalizes extremely short
    submissions.
    """
    words = stats.words

    if words < 50:
        return 20.0

    if words < 100:
        return 40.0 + (words - 50) * 0.6

    if words < 150:
        return 70.0 + (words - 100) * 0.6

    if words <= 800:
        return 100.0

    if words <= 1200:
        return 100.0 - (words - 800) * 0.08

    return 68.0


def score_structure(text: str, stats: EssayStatistics) -> float:
    score = 45.0

    if stats.paragraphs >= 3:
        score += 20
    elif stats.paragraphs == 2:
        score += 10

    if stats.sentences >= 5:
        score += 10

    if stats.average_sentence_length >= 8:
        score += 5

    if stats.average_sentence_length <= 45:
        score += 10
    else:
        score -= 10

    paragraphs = split_paragraphs(text)

    if paragraphs:
        first = paragraphs[0].lower()

        if any(
            phrase in first
            for phrase in (
                "in this essay",
                "this essay",
                "the purpose",
                "this paper",
                "i will discuss",
                "i argue",
            )
        ):
            score += 5

    if len(paragraphs) >= 3:
        last = paragraphs[-1].lower()

        if any(
            phrase in last
            for phrase in (
                "in conclusion",
                "to conclude",
                "overall",
                "ultimately",
            )
        ):
            score += 5

    return clamp(score)


def score_coherence(text: str, stats: EssayStatistics) -> float:
    score = 48.0

    transitions = stats.transition_words

    if transitions >= 5:
        score += 28
    elif transitions >= 3:
        score += 20
    elif transitions >= 1:
        score += 10

    sentences = split_sentences(text)

    if sentences:
        repetitive_starts = 0
        starts = []

        for sentence in sentences:
            words = tokenize_words(sentence)
            if words:
                starts.append(words[0])

        counts = Counter(starts)

        repetitive_starts = sum(
            max(0, count - 2)
            for count in counts.values()
        )

        score -= min(20, repetitive_starts * 3)

    return clamp(score)


def score_vocabulary(stats: EssayStatistics, text: str) -> float:
    score = 45.0

    diversity = stats.lexical_diversity

    if diversity >= 0.75:
        score += 30
    elif diversity >= 0.60:
        score += 22
    elif diversity >= 0.45:
        score += 12
    elif diversity >= 0.30:
        score += 4
    else:
        score -= 8

    if stats.long_words >= 8:
        score += 10
    elif stats.long_words >= 4:
        score += 5

    academic_count = sum(
        1
        for word in tokenize_words(text)
        if word in ACADEMIC_WORDS
    )

    if academic_count >= 5:
        score += 12
    elif academic_count >= 2:
        score += 6

    return clamp(score)


def score_sentence_quality(
    text: str,
    stats: EssayStatistics,
) -> float:
    score = 55.0

    avg_length = stats.average_sentence_length

    if 12 <= avg_length <= 28:
        score += 25
    elif 8 <= avg_length <= 35:
        score += 15
    elif avg_length < 5:
        score -= 20
    elif avg_length > 45:
        score -= 18

    sentences = split_sentences(text)

    if sentences:
        fragments = 0

        for sentence in sentences:
            words = tokenize_words(sentence)

            if len(words) < 3:
                fragments += 1

        score -= min(25, fragments * 6)

    return clamp(score)


def count_basic_spelling_issues(text: str) -> dict[str, int]:
    words = tokenize_words(text)

    result: dict[str, int] = {}

    for word in words:
        if word in COMMON_SPELLING_ERRORS:
            result[word] = result.get(word, 0) + 1

    return result


def count_repeated_words(text: str) -> list[tuple[str, int]]:
    words = [
        word
        for word in tokenize_words(text)
        if word not in STOPWORDS
    ]

    counts = Counter(words)

    return sorted(
        [
            (word, count)
            for word, count in counts.items()
            if count >= 5 and len(word) >= 4
        ],
        key=lambda item: item[1],
        reverse=True,
    )


def score_language_correctness(text: str) -> float:
    score = 88.0

    spelling_issues = count_basic_spelling_issues(text)

    score -= min(
        35,
        sum(spelling_issues.values()) * 5,
    )

    # Detect obvious punctuation spacing issues.
    punctuation_issues = len(
        re.findall(r"\s+[,.!?;:]", text)
    )

    score -= min(20, punctuation_issues * 2)

    # Detect repeated punctuation such as "!!" or "??".
    repeated_punctuation = len(
        re.findall(r"[!?]{2,}", text)
    )

    score -= min(
        15,
        repeated_punctuation * 3,
    )

    return clamp(score)


def score_content_development(text: str, stats: EssayStatistics) -> float:
    score = 45.0

    if stats.words >= 150:
        score += 20

    if stats.paragraphs >= 3:
        score += 10

    evidence_markers = (
        "for example",
        "for instance",
        "according to",
        "research",
        "study",
        "evidence",
        "data",
        "because",
        "therefore",
    )

    marker_count = sum(
        text.lower().count(marker)
        for marker in evidence_markers
    )

    if marker_count >= 5:
        score += 20
    elif marker_count >= 3:
        score += 14
    elif marker_count >= 1:
        score += 7

    return clamp(score)


# ============================================================================
# SCORING ENGINE
# ============================================================================

def generate_grade(score: float) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 80:
        return "Very Good"
    if score >= 70:
        return "Good"
    if score >= 60:
        return "Developing"
    if score >= 50:
        return "Needs Improvement"
    return "Needs Significant Improvement"


def build_criteria(
    text: str,
    stats: EssayStatistics,
) -> list[CriterionScore]:
    return [
        CriterionScore(
            name="Content & Development",
            score=round(score_content_development(text, stats), 1),
            weight=25,
            description="Development of ideas, supporting detail, and evidence signals.",
        ),
        CriterionScore(
            name="Organization",
            score=round(score_structure(text, stats), 1),
            weight=20,
            description="Paragraph structure, introduction/conclusion signals, and organization.",
        ),
        CriterionScore(
            name="Coherence",
            score=round(score_coherence(text, stats), 1),
            weight=15,
            description="Transitions, flow, and avoidance of repetitive sentence openings.",
        ),
        CriterionScore(
            name="Vocabulary",
            score=round(score_vocabulary(stats, text), 1),
            weight=15,
            description="Lexical diversity, word sophistication, and academic vocabulary signals.",
        ),
        CriterionScore(
            name="Sentence Quality",
            score=round(score_sentence_quality(text, stats), 1),
            weight=15,
            description="Sentence length balance, fragments, and readability signals.",
        ),
        CriterionScore(
            name="Language Correctness",
            score=round(score_language_correctness(text), 1),
            weight=10,
            description="Basic spelling, punctuation, and language correctness signals.",
        ),
    ]


def calculate_overall_score(
    criteria: list[CriterionScore],
) -> float:
    total_weight = sum(item.weight for item in criteria)

    if total_weight == 0:
        return 0.0

    weighted = sum(
        item.score * item.weight
        for item in criteria
    )

    return round(
        clamp(weighted / total_weight),
        1,
    )


def generate_strengths(
    text: str,
    stats: EssayStatistics,
    criteria: list[CriterionScore],
) -> list[str]:
    strengths: list[str] = []

    criterion_map = {
        item.name: item.score
        for item in criteria
    }

    if stats.words >= 150:
        strengths.append(
            "The essay has enough textual development to support a meaningful evaluation."
        )

    if criterion_map["Organization"] >= 75:
        strengths.append(
            "The essay shows a reasonably clear organizational structure."
        )

    if criterion_map["Coherence"] >= 75:
        strengths.append(
            "Transitions and connective language help the reader follow the discussion."
        )

    if criterion_map["Vocabulary"] >= 75:
        strengths.append(
            "Vocabulary usage demonstrates useful lexical variety."
        )

    if criterion_map["Sentence Quality"] >= 75:
        strengths.append(
            "Sentence construction generally maintains a readable rhythm."
        )

    if criterion_map["Language Correctness"] >= 80:
        strengths.append(
            "The basic spelling and punctuation signals are relatively clean."
        )

    if not strengths:
        strengths.append(
            "The essay provides enough material to identify concrete areas for improvement."
        )

    return strengths[:5]


def generate_improvements(
    text: str,
    stats: EssayStatistics,
    criteria: list[CriterionScore],
) -> list[str]:
    improvements: list[str] = []

    criterion_map = {
        item.name: item.score
        for item in criteria
    }

    if stats.words < 150:
        improvements.append(
            "Develop the essay with more explanation, examples, and supporting details."
        )

    if criterion_map["Organization"] < 65:
        improvements.append(
            "Strengthen the introduction, paragraph structure, and conclusion."
        )

    if criterion_map["Coherence"] < 65:
        improvements.append(
            "Use clearer transitions between ideas and paragraphs."
        )

    if criterion_map["Vocabulary"] < 65:
        improvements.append(
            "Reduce repeated wording and use more precise vocabulary where appropriate."
        )

    if criterion_map["Sentence Quality"] < 65:
        improvements.append(
            "Vary sentence length while avoiding fragments and excessively long sentences."
        )

    if criterion_map["Language Correctness"] < 75:
        improvements.append(
            "Review spelling and punctuation before submitting the essay."
        )

    spelling = count_basic_spelling_issues(text)

    if spelling:
        examples = ", ".join(
            f"{wrong} → {right}"
            for wrong, right in list(
                COMMON_SPELLING_ERRORS.items()
            )
            if wrong in spelling
        )[:180]

        improvements.append(
            f"Review likely spelling errors such as: {examples}."
        )

    repeated = count_repeated_words(text)

    if repeated:
        repeated_text = ", ".join(
            f"{word} ({count}×)"
            for word, count in repeated[:4]
        )

        improvements.append(
            f"Consider reducing repeated content words: {repeated_text}."
        )

    return improvements[:7]


def generate_warnings(
    text: str,
    stats: EssayStatistics,
) -> list[str]:
    warnings: list[str] = []

    if stats.words < MIN_ESSAY_CHARACTERS:
        warnings.append(
            "The submission is extremely short and the resulting score is not reliable."
        )

    if stats.words < 100:
        warnings.append(
            "A longer essay would provide substantially more evidence for evaluating organization and development."
        )

    if stats.sentences == 0:
        warnings.append(
            "No conventional sentences were detected."
        )

    if stats.average_sentence_length > 45:
        warnings.append(
            "Average sentence length is high; check for overly complex or run-on sentences."
        )

    if stats.paragraphs == 1 and stats.words > 200:
        warnings.append(
            "The essay is presented as one paragraph. Consider separating major ideas into paragraphs."
        )

    if text.count("!") >= 5:
        warnings.append(
            "Frequent exclamation marks may make academic writing appear less formal."
        )

    return warnings[:5]


def generate_suggestions(
    text: str,
    stats: EssayStatistics,
) -> list[str]:
    suggestions: list[str] = []

    if stats.paragraphs < 3:
        suggestions.append(
            "Try an introduction, two or more development paragraphs, and a conclusion."
        )

    if stats.transition_words < 2:
        suggestions.append(
            "Add meaningful transitions such as 'however', 'therefore', or 'for example' where logically appropriate."
        )

    if stats.lexical_diversity < 0.45:
        suggestions.append(
            "Replace unnecessary repeated words with precise alternatives."
        )

    if stats.average_sentence_length > 35:
        suggestions.append(
            "Break long sentences into smaller units when they contain multiple independent ideas."
        )

    if stats.average_sentence_length < 8 and stats.words >= 100:
        suggestions.append(
            "Combine some short sentences to create more mature sentence structures."
        )

    suggestions.append(
        "Review the essay against the assignment prompt and verify that every major claim is supported."
    )

    return suggestions[:6]


def analyze_essay(text: str) -> EssayResult:
    normalized = normalize_text(text)

    stats = calculate_statistics(normalized)
    criteria = build_criteria(normalized, stats)

    overall = calculate_overall_score(criteria)

    return EssayResult(
        overall_score=overall,
        grade=generate_grade(overall),
        statistics=stats,
        criteria=criteria,
        strengths=generate_strengths(
            normalized,
            stats,
            criteria,
        ),
        improvements=generate_improvements(
            normalized,
            stats,
            criteria,
        ),
        warnings=generate_warnings(
            normalized,
            stats,
        ),
        suggestions=generate_suggestions(
            normalized,
            stats,
        ),
        generated_at=datetime.now(
            timezone.utc
        ).isoformat(),
    )


# ============================================================================
# SAMPLE ESSAY
# ============================================================================

SAMPLE_ESSAY = """Technology has changed the way people learn, communicate, and work. 
Although digital tools can create distractions, they also provide students with 
access to information and learning opportunities that were difficult to obtain in 
the past.

One important advantage of technology is access to educational resources. For 
example, students can use digital libraries, online courses, and educational 
videos to explore subjects beyond the limits of a traditional classroom. 
Furthermore, collaborative tools allow students to work together even when they 
are physically separated. As a result, technology can make education more 
flexible and accessible.

However, technology should not be considered a replacement for thoughtful 
teaching. Excessive screen time can reduce concentration, and unreliable online 
information can lead students toward incorrect conclusions. Therefore, students 
need to develop critical thinking skills and learn how to evaluate sources.

In conclusion, technology can significantly improve education when it is used 
responsibly. The most effective approach is not to choose between traditional 
education and technology, but to combine the strengths of both approaches."""


# ============================================================================
# SESSION STATE
# ============================================================================

if "essay_text" not in st.session_state:
    st.session_state.essay_text = ""

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "analysis_count" not in st.session_state:
    st.session_state.analysis_count = 0


# ============================================================================
# HEADER
# ============================================================================

st.markdown(
    """
<div class="hero">
    <div class="brand-row">
        <div class="brand-icon">📝</div>
        <div>
            <h1>EssayScore AI</h1>
        </div>
    </div>

    <div class="hero-subtitle">
        Automated essay analysis with transparent scoring signals for
        content development, organization, coherence, vocabulary,
        sentence quality, and basic language correctness.
    </div>

    <div class="live-badge">
        <span class="live-dot"></span>
        REAL-TIME BROWSER ANALYSIS
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("## ⚙️ Analysis Settings")

    min_words = st.number_input(
        "Recommended minimum words",
        min_value=50,
        max_value=2_000,
        value=DEFAULT_MIN_WORDS,
        step=25,
    )

    max_words = st.number_input(
        "Recommended maximum words",
        min_value=100,
        max_value=5_000,
        value=DEFAULT_MAX_WORDS,
        step=50,
    )

    st.markdown("---")

    st.markdown("### Scoring dimensions")

    st.caption(
        "The scoring engine combines transparent linguistic and structural "
        "signals. It is not a trained human-rater replacement."
    )

    for label, weight in (
        ("Content & Development", "25%"),
        ("Organization", "20%"),
        ("Coherence", "15%"),
        ("Vocabulary", "15%"),
        ("Sentence Quality", "15%"),
        ("Language Correctness", "10%"),
    ):
        st.markdown(
            f"**{label}**  \n"
            f"<span style='color:#94a3b8'>{weight}</span>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    st.markdown("### 🔒 Privacy")

    st.caption(
        "Essay text is processed in the current Streamlit session. "
        "This application does not intentionally send essay content to "
        "a third-party AI provider."
    )

    st.markdown("---")

    st.caption(
        f"{APP_NAME} v{APP_VERSION}"
    )


# ============================================================================
# INPUT AREA
# ============================================================================

st.markdown(
    """
<div class="card">
    <div class="section-title">Essay Workspace</div>
    <div class="section-description">
        Paste or write your essay below. Analysis updates when you press
        <strong>Analyze Essay</strong>.
    </div>
</div>
""",
    unsafe_allow_html=True,
)

input_col, control_col = st.columns(
    [4.5, 1],
    gap="large",
)


with input_col:
    essay_text = st.text_area(
        "Essay text",
        value=st.session_state.essay_text,
        height=430,
        max_chars=MAX_ESSAY_CHARACTERS,
        placeholder=(
            "Start writing or paste your essay here...\n\n"
            "For example:\n"
            "Technology has transformed modern education..."
        ),
        label_visibility="collapsed",
    )

    live_stats = calculate_statistics(
        normalize_text(essay_text)
    )

    stat_cols = st.columns(5)

    live_metrics = [
        ("Words", live_stats.words),
        ("Characters", live_stats.characters),
        ("Sentences", live_stats.sentences),
        ("Paragraphs", live_stats.paragraphs),
        ("Unique Words", live_stats.unique_words),
    ]

    for column, (label, value) in zip(
        stat_cols,
        live_metrics,
    ):
        with column:
            st.markdown(
                f"""
<div class="metric-card">
    <div class="metric-label">{label}</div>
    <div class="metric-value">{value:,}</div>
</div>
""",
                unsafe_allow_html=True,
            )


with control_col:
    st.markdown("### Actions")

    analyze_clicked = st.button(
        "🚀 Analyze Essay",
        use_container_width=True,
        type="primary",
    )

    sample_clicked = st.button(
        "📄 Load Sample",
        use_container_width=True,
    )

    clear_clicked = st.button(
        "🗑️ Clear",
        use_container_width=True,
    )


# ============================================================================
# INPUT ACTIONS
# ============================================================================

if sample_clicked:
    st.session_state.essay_text = SAMPLE_ESSAY
    st.session_state.analysis_result = None
    st.rerun()


if clear_clicked:
    st.session_state.essay_text = ""
    st.session_state.analysis_result = None
    st.rerun()


if analyze_clicked:
    cleaned = normalize_text(essay_text)

    if len(cleaned) < MIN_ESSAY_CHARACTERS:
        st.error(
            "Please enter a longer essay before starting the analysis."
        )
    elif len(cleaned) > MAX_ESSAY_CHARACTERS:
        st.error(
            f"Essay exceeds the {MAX_ESSAY_CHARACTERS:,}-character limit."
        )
    else:
        with st.spinner("Analyzing essay structure and language..."):
            result = analyze_essay(cleaned)

        st.session_state.essay_text = cleaned
        st.session_state.analysis_result = result
        st.session_state.analysis_count += 1


# ============================================================================
# RESULTS
# ============================================================================

result: EssayResult | None = st.session_state.analysis_result

if result is None:
    st.markdown(
        """
<div class="card" style="text-align:center; padding:2.5rem 1.5rem;">
    <div style="font-size:2.5rem;">📊</div>
    <div class="section-title" style="margin-top:0.6rem;">
        Ready to analyze
    </div>
    <div class="section-description" style="max-width:650px; margin:0.5rem auto;">
        Enter an essay and select <strong>Analyze Essay</strong> to receive
        a transparent breakdown of writing quality signals.
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

else:
    # ------------------------------------------------------------------------
    # SCORE OVERVIEW
    # ------------------------------------------------------------------------

    st.markdown("---")

    st.markdown(
        """
<div class="section-title">Analysis Overview</div>
<div class="section-description">
    Your score is an analytical estimate based on observable text features.
</div>
""",
        unsafe_allow_html=True,
    )

    score_col, metrics_col = st.columns(
        [1.2, 3],
        gap="large",
    )

    with score_col:
        score_color = (
            "#34d399"
            if result.overall_score >= 80
            else "#fbbf24"
            if result.overall_score >= 60
            else "#fb7185"
        )

        st.markdown(
            f"""
<div class="score-panel">
    <div class="score-number" style="color:{score_color}">
        {result.overall_score:.1f}
    </div>
    <div class="score-denominator">/ 100</div>
    <div class="score-label">{result.grade}</div>
    <div class="score-description">
        Overall analytical score
    </div>
</div>
""",
            unsafe_allow_html=True,
        )

    with metrics_col:
        metric_rows = [
            ("Words", result.statistics.words, "Total detected words"),
            (
                "Sentences",
                result.statistics.sentences,
                "Detected sentence units",
            ),
            (
                "Paragraphs",
                result.statistics.paragraphs,
                "Detected paragraphs",
            ),
            (
                "Vocabulary",
                f"{result.statistics.lexical_diversity * 100:.0f}%",
                "Content-word lexical diversity",
            ),
            (
                "Avg. Sentence",
                f"{result.statistics.average_sentence_length:.1f}",
                "Words per sentence",
            ),
            (
                "Transitions",
                result.statistics.transition_words,
                "Detected transition signals",
            ),
        ]

        metric_grid = st.columns(3)

        for column, (
            label,
            value,
            description,
        ) in zip(
            metric_grid * 2,
            metric_rows,
        ):
            with column:
                st.markdown(
                    f"""
<div class="metric-card">
    <div class="metric-label">{label}</div>
    <div class="metric-value">{value}</div>
    <div class="metric-help">{description}</div>
</div>
""",
                    unsafe_allow_html=True,
                )

    # ------------------------------------------------------------------------
    # CRITERIA
    # ------------------------------------------------------------------------

    st.markdown("### Score Breakdown")

    for criterion in result.criteria:
        col1, col2 = st.columns(
            [3.5, 1],
            vertical_alignment="center",
        )

        with col1:
            st.markdown(
                f"**{criterion.name}**  \n"
                f"<span style='color:#94a3b8;font-size:0.8rem'>"
                f"{criterion.description}"
                f"</span>",
                unsafe_allow_html=True,
            )

            st.progress(
                int(round(criterion.score))
            )

        with col2:
            st.markdown(
                f"""
<div style="
    text-align:right;
    font-size:1.5rem;
    font-weight:800;
    color:#f8fafc;
">
    {criterion.score:.0f}
    <span style="
        color:#94a3b8;
        font-size:0.72rem;
        font-weight:500;
    ">
        / 100
    </span>
</div>
""",
                unsafe_allow_html=True,
            )

    # ------------------------------------------------------------------------
    # FINDINGS
    # ------------------------------------------------------------------------

    st.markdown("### Writing Insights")

    left, right = st.columns(
        2,
        gap="large",
    )

    with left:
        st.markdown("#### ✅ Strengths")

        for strength in result.strengths:
            st.markdown(
                f"""
<div class="finding finding-success">
    <div class="finding-title">Positive signal</div>
    <div class="finding-body">{strength}</div>
</div>
""",
                unsafe_allow_html=True,
            )

        st.markdown("#### 🔧 Areas for Improvement")

        for improvement in result.improvements:
            st.markdown(
                f"""
<div class="finding finding-warning">
    <div class="finding-title">Improvement opportunity</div>
    <div class="finding-body">{improvement}</div>
</div>
""",
                unsafe_allow_html=True,
            )

    with right:
        st.markdown("#### 💡 Suggestions")

        for suggestion in result.suggestions:
            st.markdown(
                f"""
<div class="finding finding-info">
    <div class="finding-title">Recommendation</div>
    <div class="finding-body">{suggestion}</div>
</div>
""",
                unsafe_allow_html=True,
            )

        if result.warnings:
            st.markdown("#### ⚠️ Evaluation Warnings")

            for warning in result.warnings:
                st.markdown(
                    f"""
<div class="finding finding-danger">
    <div class="finding-title">Attention</div>
    <div class="finding-body">{warning}</div>
</div>
""",
                    unsafe_allow_html=True,
                )

    # ------------------------------------------------------------------------
    # DETAILED STATISTICS
    # ------------------------------------------------------------------------

    with st.expander("📐 Detailed Text Statistics"):
        detail_cols = st.columns(4)

        details = [
            (
                "Characters",
                f"{result.statistics.characters:,}",
            ),
            (
                "Characters excluding spaces",
                f"{result.statistics.characters_no_spaces:,}",
            ),
            (
                "Average word length",
                f"{result.statistics.average_word_length:.2f}",
            ),
            (
                "Average sentence length",
                f"{result.statistics.average_sentence_length:.2f}",
            ),
            (
                "Unique content words",
                f"{result.statistics.unique_words:,}",
            ),
            (
                "Lexical diversity",
                f"{result.statistics.lexical_diversity:.3f}",
            ),
            (
                "Long words",
                f"{result.statistics.long_words:,}",
            ),
            (
                "Transition signals",
                f"{result.statistics.transition_words:,}",
            ),
        ]

        for index, (
            label,
            value,
        ) in enumerate(details):
            with detail_cols[index % 4]:
                st.metric(
                    label,
                    value,
                )

    # ------------------------------------------------------------------------
    # BASIC SPELLING REVIEW
    # ------------------------------------------------------------------------

    spelling_issues = count_basic_spelling_issues(
        st.session_state.essay_text
    )

    with st.expander("🔤 Basic Spelling Review"):
        if spelling_issues:
            st.warning(
                "Potential spelling errors were detected. "
                "Review these suggestions manually."
            )

            for wrong, count in spelling_issues.items():
                st.write(
                    f"**{wrong}** → `{COMMON_SPELLING_ERRORS[wrong]}` "
                    f"({count} occurrence{'s' if count != 1 else ''})"
                )
        else:
            st.success(
                "No matches from the application's basic spelling-error dictionary were detected."
            )

        st.caption(
            "This is a limited rule-based review, not a full spell checker."
        )

    # ------------------------------------------------------------------------
    # DOWNLOAD
    # ------------------------------------------------------------------------

    st.markdown("### Export")

    export_payload = {
        "application": APP_NAME,
        "version": APP_VERSION,
        "generated_at": result.generated_at,
        "overall_score": result.overall_score,
        "grade": result.grade,
        "statistics": asdict(result.statistics),
        "criteria": [
            asdict(item)
            for item in result.criteria
        ],
        "strengths": result.strengths,
        "improvements": result.improvements,
        "warnings": result.warnings,
        "suggestions": result.suggestions,
    }

    import json

    export_json = json.dumps(
        export_payload,
        indent=2,
        ensure_ascii=False,
    )

    st.download_button(
        label="⬇️ Download Analysis JSON",
        data=export_json,
        file_name="essay-analysis.json",
        mime="application/json",
    )


# ============================================================================
# DISCLAIMER
# ============================================================================

st.markdown(
    """
<div class="footer">
    <strong>Important:</strong>
    This application provides an automated analytical estimate based on
    transparent text features and heuristic rules. It is not a certified
    examination scorer and should not be treated as equivalent to evaluation
    by a trained human examiner or a validated educational assessment model.
    <br><br>
    No browser GPS data is collected. The application is designed to analyze
    the essay text supplied by the user and does not require an external
    generative-AI service.
    <br><br>
    © 2026 EssayScore AI
</div>
""",
    unsafe_allow_html=True,
)