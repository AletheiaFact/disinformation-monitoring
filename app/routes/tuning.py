"""Tuning endpoints for testing and optimizing extraction and filtering logic"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict
import feedparser
import logging
from pathlib import Path

from app.filters.pre_filter import PreFilter
from app.nlp.claim_extractor import extract_checkable_content, ClaimExtractor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tuning", tags=["tuning"])


@router.post("/test-feed")
async def test_feed_extraction():
    """
    Test extraction and scoring against the tuning RSS feed.

    Returns detailed results for each item including:
    - Expected vs actual scores
    - Extraction quality
    - Claim detection results
    - Pass/fail status
    """
    # Load the tuning feed
    feed_path = Path("/app/tests/fixtures/tuning_feed.xml")

    if not feed_path.exists():
        raise HTTPException(status_code=404, detail="Tuning feed not found")

    # Parse RSS feed
    feed = feedparser.parse(str(feed_path))

    if not feed.entries:
        raise HTTPException(status_code=400, detail="No entries found in tuning feed")

    results = []
    pre_filter = PreFilter()
    claim_extractor = ClaimExtractor()

    for entry in feed.entries:
        try:
            # Extract data
            title = entry.get('title', '').strip()
            raw_content = entry.get('description', '') or entry.get('summary', '')
            url = entry.get('link', '')

            # Get expected category
            categories = [cat.get('term', '') for cat in entry.get('tags', [])]
            expected_quality = next((cat for cat in categories if cat.startswith('EXPECTED:')), 'UNKNOWN')
            test_description = next((cat for cat in categories if not cat.startswith('EXPECTED:')), '')

            # Extract fact-checkable content
            extracted_content = extract_checkable_content(raw_content, max_chars=500)

            # Calculate pre-filter score
            score_breakdown = pre_filter.calculate_score(
                content=extracted_content,
                title=title,
                source_url=url,
                credibility_level='low'  # Assume low for testing (highest priority)
            )

            # Extract claims with attribution
            claims = claim_extractor.extract_claims_with_attribution(extracted_content)

            # Determine pass/fail based on expected quality
            expected_range = _parse_expected_range(expected_quality)
            passed = _check_score_in_range(score_breakdown['total'], expected_range)

            # Compile result
            result = {
                'title': title,
                'url': url,
                'expected_quality': expected_quality,
                'test_description': test_description,
                'extracted_content': extracted_content,
                'extracted_length': len(extracted_content),
                'score': score_breakdown['total'],
                'score_breakdown': score_breakdown,
                'expected_range': expected_range,
                'passed': passed,
                'deviation': _calculate_deviation(score_breakdown['total'], expected_range),
                'claims_found': len(claims),
                'claims': claims[:3],  # Top 3 claims
                'has_attribution': len(claims) > 0,
                'has_government_entity': any(c.get('has_government_entity') for c in claims),
                'has_data': any(c.get('has_data') for c in claims)
            }

            results.append(result)

        except Exception as e:
            logger.error(f"Error processing tuning entry: {e}")
            results.append({
                'title': entry.get('title', 'ERROR'),
                'error': str(e),
                'passed': False
            })

    # Calculate summary statistics
    summary = _calculate_summary(results)

    return {
        'summary': summary,
        'results': results
    }


@router.post("/test-single")
async def test_single_content(
    title: str,
    content: str,
    expected_score_min: int = 0,
    expected_score_max: int = 60
):
    """
    Test extraction and scoring for a single piece of content.

    Useful for quick testing of specific examples.
    """
    pre_filter = PreFilter()
    claim_extractor = ClaimExtractor()

    # Extract fact-checkable content
    extracted_content = extract_checkable_content(content, max_chars=500)

    # Calculate score
    score_breakdown = pre_filter.calculate_score(
        content=extracted_content,
        title=title,
        source_url="http://test.example.com/single-test",
        credibility_level='low'
    )

    # Extract claims
    claims = claim_extractor.extract_claims_with_attribution(extracted_content)

    # Check if passed
    passed = expected_score_min <= score_breakdown['total'] <= expected_score_max

    return {
        'title': title,
        'original_content': content,
        'extracted_content': extracted_content,
        'extracted_length': len(extracted_content),
        'score': score_breakdown['total'],
        'score_breakdown': score_breakdown,
        'expected_range': [expected_score_min, expected_score_max],
        'passed': passed,
        'claims_found': len(claims),
        'claims': claims
    }


@router.get("/scoring-guide")
async def get_scoring_guide():
    """
    Get the scoring guide for reference.

    Returns the complete scoring breakdown and thresholds.
    """
    return {
        'scoring_components': {
            'content_quality': {
                'max_points': 20,
                'factors': {
                    'length': {
                        '>=300 chars': 10,
                        '>=150 chars': 7,
                        '>=100 chars': 5,
                        '<100 chars': 0
                    },
                    'sentences': {
                        '>=3 sentences': 10,
                        '2 sentences': 7,
                        '1 sentence': 3,
                        '0 sentences': 0
                    }
                }
            },
            'fact_checkable': {
                'max_points': 30,
                'factors': {
                    'government_entities': 18,
                    'political_keywords': 15,
                    'social_relevance': 12,
                    'health_science': 10,
                    'attribution': 8,
                    'verifiable_data': '3-6 (percentage=6, currency=6, large_numbers=5, dates=4, numbers=3)'
                }
            },
            'source_risk': {
                'max_points': 10,
                'inverted': True,
                'factors': {
                    'low_credibility': 10,
                    'medium_credibility': 5,
                    'high_credibility': 3
                }
            },
            'topic_penalty': {
                'max_penalty': -30,
                'factors': {
                    'entertainment_heavy': -25,
                    'entertainment_medium': -20,
                    'entertainment_light': -15,
                    'sports_heavy': -15,
                    'sports_medium': -10
                },
                'controversy_override': 'Sports + corruption = no penalty'
            }
        },
        'thresholds': {
            'minimum_save': 20,
            'submission_threshold': 35,
            'explanation': 'Score < 20: not saved | Score 20-34: saved but rejected | Score >= 35: submitted'
        },
        'expected_ranges': {
            'high_quality': '50-60 points (government + data + attribution)',
            'medium_quality': '30-45 points (some checkable elements, missing data)',
            'low_quality': '0-25 points (entertainment, sports, vague language)',
            'noise': '0-10 points (pure noise, navigation, metadata)'
        }
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _parse_expected_range(expected_str: str) -> List[int]:
    """
    Parse expected quality string to score range.

    Examples:
    - "EXPECTED: HIGH (55-60 points)" -> [55, 60]
    - "EXPECTED: LOW (0-10 points)" -> [0, 10]
    - "EXPECTED: ZERO (0 points)" -> [0, 5]
    """
    import re

    if 'ZERO' in expected_str or '(0 points)' in expected_str:
        return [0, 5]

    # Extract range like (55-60 points) or (0-10)
    match = re.search(r'\((\d+)-(\d+)', expected_str)
    if match:
        return [int(match.group(1)), int(match.group(2))]

    # Default ranges based on keywords
    if 'HIGH' in expected_str:
        return [50, 60]
    elif 'MEDIUM' in expected_str or 'LOW-MEDIUM' in expected_str:
        return [25, 45]
    elif 'LOW' in expected_str or 'VERY LOW' in expected_str:
        return [0, 25]
    else:
        return [0, 60]  # Unknown - accept any score


def _check_score_in_range(score: int, expected_range: List[int]) -> bool:
    """Check if score falls within expected range (with 5-point tolerance)"""
    tolerance = 5
    return (expected_range[0] - tolerance) <= score <= (expected_range[1] + tolerance)


def _calculate_deviation(score: int, expected_range: List[int]) -> int:
    """Calculate how far the score deviates from expected range"""
    if expected_range[0] <= score <= expected_range[1]:
        return 0  # Within range
    elif score < expected_range[0]:
        return score - expected_range[0]  # Negative (too low)
    else:
        return score - expected_range[1]  # Positive (too high)


def _calculate_summary(results: List[Dict]) -> Dict:
    """Calculate summary statistics from test results"""
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.get('passed', False))
    failed_tests = total_tests - passed_tests

    # Calculate by expected category
    high_quality = [r for r in results if 'HIGH' in r.get('expected_quality', '')]
    medium_quality = [r for r in results if 'MEDIUM' in r.get('expected_quality', '')]
    low_quality = [r for r in results if 'LOW' in r.get('expected_quality', '')]
    edge_cases = [r for r in results if 'edge-case' in r.get('url', '')]

    return {
        'total_tests': total_tests,
        'passed': passed_tests,
        'failed': failed_tests,
        'pass_rate': f"{(passed_tests / total_tests * 100):.1f}%" if total_tests > 0 else "0%",
        'by_category': {
            'high_quality': {
                'count': len(high_quality),
                'passed': sum(1 for r in high_quality if r.get('passed')),
                'avg_score': sum(r.get('score', 0) for r in high_quality) / len(high_quality) if high_quality else 0
            },
            'medium_quality': {
                'count': len(medium_quality),
                'passed': sum(1 for r in medium_quality if r.get('passed')),
                'avg_score': sum(r.get('score', 0) for r in medium_quality) / len(medium_quality) if medium_quality else 0
            },
            'low_quality': {
                'count': len(low_quality),
                'passed': sum(1 for r in low_quality if r.get('passed')),
                'avg_score': sum(r.get('score', 0) for r in low_quality) / len(low_quality) if low_quality else 0
            },
            'edge_cases': {
                'count': len(edge_cases),
                'passed': sum(1 for r in edge_cases if r.get('passed')),
                'avg_score': sum(r.get('score', 0) for r in edge_cases) / len(edge_cases) if edge_cases else 0
            }
        },
        'problematic_tests': [
            {
                'title': r['title'],
                'expected': r['expected_quality'],
                'actual_score': r['score'],
                'deviation': r.get('deviation', 0)
            }
            for r in results if not r.get('passed', False) and 'error' not in r
        ]
    }
