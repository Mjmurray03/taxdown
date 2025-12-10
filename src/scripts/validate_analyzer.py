"""
Assessment Analyzer Validation Script

This script validates and calibrates the Assessment Analyzer against real Benton County data.
It performs statistical validation, comparable quality checks, edge case identification,
and generates calibration recommendations.

Usage:
    python src/scripts/validate_analyzer.py [--sample-size N]
"""

import sys
import os
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import statistics
from collections import Counter, defaultdict

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from config import get_engine
from services.assessment_analyzer import AssessmentAnalyzer, AssessmentAnalysis
from services.comparable_service import ComparableService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnalyzerValidator:
    """
    Validates the Assessment Analyzer against real data.
    """

    def __init__(self, engine: Engine, sample_size: int = 500):
        """
        Initialize the validator.

        Args:
            engine: SQLAlchemy database engine
            sample_size: Number of properties to sample for validation
        """
        self.engine = engine
        self.sample_size = sample_size
        self.analyzer = AssessmentAnalyzer(engine, default_mill_rate=65.0)
        self.comparable_service = ComparableService(engine)

        # Validation results storage
        self.analyses: List[AssessmentAnalysis] = []
        self.edge_cases: Dict[str, List[AssessmentAnalysis]] = {
            'zero_comparables': [],
            'extreme_scores': [],
            'unusual_ratios': []
        }
        self.comparable_quality_data: List[Dict[str, Any]] = []

    def run_full_validation(self) -> Dict[str, Any]:
        """
        Run complete validation suite.

        Returns:
            Dictionary with all validation results
        """
        logger.info(f"Starting full validation with sample size: {self.sample_size}")

        # Step 1: Get random sample of properties
        property_ids = self._get_random_sample()
        logger.info(f"Retrieved {len(property_ids)} properties for analysis")

        # Step 2: Analyze all properties
        self._analyze_properties(property_ids)
        logger.info(f"Analyzed {len(self.analyses)} properties successfully")

        # Step 3: Statistical validation
        fairness_stats = self._validate_fairness_distribution()
        ratio_stats = self._validate_assessment_ratios()
        savings_stats = self._validate_savings_estimates()

        # Step 4: Comparable quality check (subset of 50)
        comparable_stats = self._check_comparable_quality(min(50, len(property_ids)))

        # Step 5: Edge case identification
        edge_case_stats = self._identify_edge_cases()

        # Step 6: Generate reports
        results = {
            'sample_size': len(self.analyses),
            'analysis_date': datetime.now(),
            'fairness_distribution': fairness_stats,
            'assessment_ratios': ratio_stats,
            'savings_estimates': savings_stats,
            'comparable_quality': comparable_stats,
            'edge_cases': edge_case_stats
        }

        return results

    def _get_random_sample(self) -> List[str]:
        """
        Get random sample of properties with valid assessment data.

        Returns:
            List of parcel IDs
        """
        query = text("""
            SELECT parcel_id
            FROM properties
            WHERE assess_val_cents > 0
                AND total_val_cents > 0
                AND parcel_id IS NOT NULL
                AND is_active = true
            ORDER BY RANDOM()
            LIMIT :limit
        """)

        with self.engine.connect() as conn:
            result = conn.execute(query, {"limit": self.sample_size})
            return [row.parcel_id for row in result.fetchall()]

    def _analyze_properties(self, property_ids: List[str]) -> None:
        """
        Analyze all properties and store results.

        Args:
            property_ids: List of parcel IDs to analyze
        """
        logger.info(f"Analyzing {len(property_ids)} properties...")

        for i, prop_id in enumerate(property_ids, 1):
            if i % 50 == 0:
                logger.info(f"Progress: {i}/{len(property_ids)} ({i/len(property_ids)*100:.1f}%)")

            try:
                analysis = self.analyzer.analyze_property(prop_id)
                if analysis:
                    self.analyses.append(analysis)
            except Exception as e:
                logger.warning(f"Failed to analyze property {prop_id}: {e}")

    def _validate_fairness_distribution(self) -> Dict[str, Any]:
        """
        Validate fairness score distribution.

        Returns:
            Dictionary with distribution statistics and validation results
        """
        logger.info("Validating fairness score distribution...")

        scores = [a.fairness_score for a in self.analyses]

        if not scores:
            return {'error': 'No scores to analyze'}

        # Calculate distribution
        distribution = {
            '0-20': sum(1 for s in scores if 0 <= s <= 20),
            '21-40': sum(1 for s in scores if 21 <= s <= 40),
            '41-60': sum(1 for s in scores if 41 <= s <= 60),
            '61-80': sum(1 for s in scores if 61 <= s <= 80),
            '81-100': sum(1 for s in scores if 81 <= s <= 100)
        }

        total = len(scores)
        distribution_pct = {k: (v / total * 100) for k, v in distribution.items()}

        # Calculate statistics
        median_score = statistics.median(scores)
        mean_score = statistics.mean(scores)
        std_score = statistics.stdev(scores) if len(scores) > 1 else 0

        # Count appeal candidates
        over_assessed_count = sum(1 for s in scores if s > 60)
        over_assessed_pct = (over_assessed_count / total * 100) if total > 0 else 0

        severely_over_count = sum(1 for s in scores if s > 80)
        severely_over_pct = (severely_over_count / total * 100) if total > 0 else 0

        # Validation checks
        checks = {
            'median_in_range': 30 <= median_score <= 40,
            'appeal_rate_reasonable': 10 <= over_assessed_pct <= 15,
            'severe_cases_low': severely_over_pct < 5
        }

        return {
            'distribution': distribution,
            'distribution_pct': distribution_pct,
            'median': median_score,
            'mean': mean_score,
            'std_dev': std_score,
            'over_assessed_count': over_assessed_count,
            'over_assessed_pct': over_assessed_pct,
            'severely_over_count': severely_over_count,
            'severely_over_pct': severely_over_pct,
            'validation_checks': checks
        }

    def _validate_assessment_ratios(self) -> Dict[str, Any]:
        """
        Validate assessment ratio distribution.

        Returns:
            Dictionary with ratio statistics and validation results
        """
        logger.info("Validating assessment ratios...")

        ratios = [a.current_ratio for a in self.analyses]

        if not ratios:
            return {'error': 'No ratios to analyze'}

        # Convert to percentages for readability
        ratios_pct = [r * 100 for r in ratios]

        median_ratio = statistics.median(ratios_pct)
        mean_ratio = statistics.mean(ratios_pct)
        std_ratio = statistics.stdev(ratios_pct) if len(ratios_pct) > 1 else 0

        # Count outliers
        outliers_low = sum(1 for r in ratios_pct if r < 10)
        outliers_high = sum(1 for r in ratios_pct if r > 30)
        total = len(ratios_pct)

        outliers_pct = ((outliers_low + outliers_high) / total * 100) if total > 0 else 0

        # Validation checks (Arkansas statutory rate is ~20%)
        checks = {
            'median_near_statutory': 18 <= median_ratio <= 22,
            'std_dev_reasonable': std_ratio <= 5,
            'outliers_low': outliers_pct < 10
        }

        return {
            'median_pct': median_ratio,
            'mean_pct': mean_ratio,
            'std_dev_pct': std_ratio,
            'min_pct': min(ratios_pct),
            'max_pct': max(ratios_pct),
            'outliers_low': outliers_low,
            'outliers_high': outliers_high,
            'outliers_pct': outliers_pct,
            'validation_checks': checks
        }

    def _validate_savings_estimates(self) -> Dict[str, Any]:
        """
        Validate savings estimate sanity.

        Returns:
            Dictionary with savings statistics and validation results
        """
        logger.info("Validating savings estimates...")

        # Filter for appeal candidates only (score <= 60 means over-assessed)
        # NEW SCORING: higher score = FAIRER, so appeal candidates have LOWER scores
        appeal_candidates = [a for a in self.analyses if a.fairness_score <= 60]

        if not appeal_candidates:
            return {'error': 'No appeal candidates found'}

        savings = [a.estimated_annual_savings_cents / 100 for a in appeal_candidates]

        median_savings = statistics.median(savings)
        mean_savings = statistics.mean(savings)
        std_savings = statistics.stdev(savings) if len(savings) > 1 else 0

        # Check for extreme values
        extreme_savings = [s for s in savings if s > 10000]
        extreme_count = len(extreme_savings)

        # Calculate total potential savings
        total_potential = sum(s for s in savings)

        # Validation checks
        checks = {
            'mean_in_range': 200 <= mean_savings <= 2000,
            'no_extreme_outliers': extreme_count == 0,
            'positive_savings': all(s > 0 for s in savings)
        }

        return {
            'appeal_candidates': len(appeal_candidates),
            'median_savings': median_savings,
            'mean_savings': mean_savings,
            'std_dev_savings': std_savings,
            'min_savings': min(savings),
            'max_savings': max(savings),
            'extreme_count': extreme_count,
            'total_potential': total_potential,
            'validation_checks': checks
        }

    def _check_comparable_quality(self, sample_count: int) -> Dict[str, Any]:
        """
        Check quality of comparable matching for a sample.

        Args:
            sample_count: Number of properties to check

        Returns:
            Dictionary with comparable quality statistics
        """
        logger.info(f"Checking comparable quality for {sample_count} properties...")

        sample_analyses = self.analyses[:sample_count]
        comparable_counts = []
        value_similarity_scores = []

        for analysis in sample_analyses:
            comparable_counts.append(analysis.comparable_count)

            # Get detailed comparables to check similarity
            try:
                comparables = self.comparable_service.find_comparables(
                    analysis.parcel_id,
                    limit=20
                )

                if comparables and analysis.total_val_cents > 0:
                    # Check value similarity
                    subject_value = analysis.total_val_cents
                    similar_count = sum(
                        1 for comp in comparables
                        if 0.8 <= (comp.total_val_cents / subject_value) <= 1.2
                    )
                    similarity_pct = (similar_count / len(comparables) * 100) if comparables else 0
                    value_similarity_scores.append(similarity_pct)

            except Exception as e:
                logger.warning(f"Error checking comparables for {analysis.parcel_id}: {e}")

        avg_comparable_count = statistics.mean(comparable_counts) if comparable_counts else 0
        median_comparable_count = statistics.median(comparable_counts) if comparable_counts else 0

        avg_similarity = statistics.mean(value_similarity_scores) if value_similarity_scores else 0

        # Validation checks
        checks = {
            'avg_count_in_range': 10 <= avg_comparable_count <= 20,
            'similarity_reasonable': avg_similarity >= 60
        }

        return {
            'sample_size': sample_count,
            'avg_comparable_count': avg_comparable_count,
            'median_comparable_count': median_comparable_count,
            'min_comparable_count': min(comparable_counts) if comparable_counts else 0,
            'max_comparable_count': max(comparable_counts) if comparable_counts else 0,
            'avg_value_similarity_pct': avg_similarity,
            'validation_checks': checks
        }

    def _identify_edge_cases(self) -> Dict[str, Any]:
        """
        Identify and categorize edge cases.

        Returns:
            Dictionary with edge case statistics
        """
        logger.info("Identifying edge cases...")

        # Zero comparables
        zero_comps = [a for a in self.analyses if a.comparable_count == 0]
        self.edge_cases['zero_comparables'] = zero_comps

        # Extreme scores
        extreme_scores = [a for a in self.analyses if a.fairness_score <= 10 or a.fairness_score >= 90]
        self.edge_cases['extreme_scores'] = extreme_scores

        # Unusual ratios
        unusual_ratios = [a for a in self.analyses if a.current_ratio < 0.10 or a.current_ratio > 0.30]
        self.edge_cases['unusual_ratios'] = unusual_ratios

        return {
            'zero_comparables': {
                'count': len(zero_comps),
                'percentage': (len(zero_comps) / len(self.analyses) * 100) if self.analyses else 0
            },
            'extreme_scores': {
                'count': len(extreme_scores),
                'percentage': (len(extreme_scores) / len(self.analyses) * 100) if self.analyses else 0,
                'examples': [
                    {
                        'parcel_id': a.parcel_id,
                        'score': a.fairness_score,
                        'ratio': a.current_ratio
                    }
                    for a in extreme_scores[:5]
                ]
            },
            'unusual_ratios': {
                'count': len(unusual_ratios),
                'percentage': (len(unusual_ratios) / len(self.analyses) * 100) if self.analyses else 0,
                'examples': [
                    {
                        'parcel_id': a.parcel_id,
                        'ratio': a.current_ratio,
                        'score': a.fairness_score
                    }
                    for a in unusual_ratios[:5]
                ]
            }
        }

    def generate_histogram(self, output_path: str) -> None:
        """
        Generate fairness score distribution histogram.

        Args:
            output_path: Path to save the histogram
        """
        logger.info(f"Generating histogram: {output_path}")

        scores = [a.fairness_score for a in self.analyses]

        if not scores:
            logger.warning("No scores to plot")
            return

        plt.figure(figsize=(12, 7))

        # Create histogram
        n, bins, patches = plt.hist(scores, bins=20, edgecolor='black', alpha=0.7)

        # Color bars by category
        for i, patch in enumerate(patches):
            bin_center = (bins[i] + bins[i+1]) / 2
            if bin_center <= 20:
                patch.set_facecolor('#2ecc71')  # Green - under-assessed
            elif bin_center <= 40:
                patch.set_facecolor('#3498db')  # Blue - fair
            elif bin_center <= 60:
                patch.set_facecolor('#f39c12')  # Orange - monitor
            elif bin_center <= 80:
                patch.set_facecolor('#e74c3c')  # Red - appeal
            else:
                patch.set_facecolor('#c0392b')  # Dark red - strong appeal

        plt.xlabel('Fairness Score', fontsize=12)
        plt.ylabel('Number of Properties', fontsize=12)
        plt.title('Assessment Fairness Score Distribution\n'
                  f'Sample Size: {len(scores)} properties', fontsize=14, fontweight='bold')

        # Add statistics
        median = statistics.median(scores)
        mean = statistics.mean(scores)
        std = statistics.stdev(scores) if len(scores) > 1 else 0

        stats_text = f'Median: {median:.1f}\nMean: {mean:.1f}\nStd Dev: {std:.1f}'
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,
                 fontsize=10, verticalalignment='top',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#2ecc71', label='Under-assessed (0-20)'),
            Patch(facecolor='#3498db', label='Fair (21-40)'),
            Patch(facecolor='#f39c12', label='Monitor (41-60)'),
            Patch(facecolor='#e74c3c', label='Appeal (61-80)'),
            Patch(facecolor='#c0392b', label='Strong Appeal (81-100)')
        ]
        plt.legend(handles=legend_elements, loc='upper right')

        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Histogram saved to {output_path}")

    def generate_validation_report(self, results: Dict[str, Any], output_path: str) -> None:
        """
        Generate markdown validation report.

        Args:
            results: Validation results dictionary
            output_path: Path to save the report
        """
        logger.info(f"Generating validation report: {output_path}")

        fairness = results['fairness_distribution']
        ratios = results['assessment_ratios']
        savings = results['savings_estimates']
        comparables = results['comparable_quality']
        edges = results['edge_cases']

        report = f"""# Assessment Analyzer Validation Report

**Analysis Date:** {results['analysis_date'].strftime('%Y-%m-%d %H:%M:%S')}
**Sample Size:** {results['sample_size']} properties

---

## Executive Summary

This report validates the Assessment Analyzer's output against real Benton County property data.
The analysis examines fairness score distributions, assessment ratios, savings estimates,
comparable matching quality, and edge cases.

---

## 1. Fairness Score Distribution

### Distribution Breakdown

| Range | Count | Percentage | Status |
|-------|-------|------------|--------|
| 0-20 (Under-assessed) | {fairness['distribution']['0-20']} | {fairness['distribution_pct']['0-20']:.1f}% | - |
| 21-40 (Fair) | {fairness['distribution']['21-40']} | {fairness['distribution_pct']['21-40']:.1f}% | - |
| 41-60 (Monitor) | {fairness['distribution']['41-60']} | {fairness['distribution_pct']['41-60']:.1f}% | - |
| 61-80 (Appeal) | {fairness['distribution']['61-80']} | {fairness['distribution_pct']['61-80']:.1f}% | - |
| 81-100 (Strong Appeal) | {fairness['distribution']['81-100']} | {fairness['distribution_pct']['81-100']:.1f}% | - |

### Statistical Summary

- **Median Score:** {fairness['median']:.1f} {'✓' if fairness['validation_checks']['median_in_range'] else '✗'} (expected: 30-40)
- **Mean Score:** {fairness['mean']:.1f}
- **Standard Deviation:** {fairness['std_dev']:.1f}
- **Over-assessed (>60):** {fairness['over_assessed_count']} ({fairness['over_assessed_pct']:.1f}%) {'✓' if fairness['validation_checks']['appeal_rate_reasonable'] else '✗'} (expected: 10-15%)
- **Severely Over-assessed (>80):** {fairness['severely_over_count']} ({fairness['severely_over_pct']:.1f}%) {'✓' if fairness['validation_checks']['severe_cases_low'] else '✗'} (expected: <5%)

### Validation Status

"""
        for check, passed in fairness['validation_checks'].items():
            status = '✓ PASS' if passed else '✗ FAIL'
            report += f"- {check.replace('_', ' ').title()}: {status}\n"

        report += f"""
---

## 2. Assessment Ratio Validation

Assessment ratios represent the assessed value as a percentage of total market value.
Arkansas statutory rate is approximately 20% for residential properties.

### Statistics

- **Median Ratio:** {ratios['median_pct']:.2f}% {'✓' if ratios['validation_checks']['median_near_statutory'] else '✗'} (expected: ~20%)
- **Mean Ratio:** {ratios['mean_pct']:.2f}%
- **Standard Deviation:** {ratios['std_dev_pct']:.2f}% {'✓' if ratios['validation_checks']['std_dev_reasonable'] else '✗'} (expected: 2-5%)
- **Range:** {ratios['min_pct']:.2f}% to {ratios['max_pct']:.2f}%

### Data Quality Issues

- **Ratios < 10%:** {ratios['outliers_low']} properties
- **Ratios > 30%:** {ratios['outliers_high']} properties
- **Total Outliers:** {ratios['outliers_low'] + ratios['outliers_high']} ({ratios['outliers_pct']:.1f}%) {'✓' if ratios['validation_checks']['outliers_low'] else '✗'}

---

## 3. Savings Estimate Validation

Analysis of estimated annual tax savings for appeal candidates (fairness score <= 60, lower = more over-assessed).

"""
        if 'error' not in savings:
            report += f"""### Statistics

- **Appeal Candidates:** {savings['appeal_candidates']}
- **Median Savings:** ${savings['median_savings']:,.2f}/year
- **Mean Savings:** ${savings['mean_savings']:,.2f}/year {'✓' if savings['validation_checks']['mean_in_range'] else '✗'} (expected: $200-$2,000)
- **Range:** ${savings['min_savings']:,.2f} to ${savings['max_savings']:,.2f}
- **Total Potential County-wide:** ${savings['total_potential']:,.2f}/year

### Data Quality

- **Extreme Savings (>$10,000):** {savings['extreme_count']} {'✓' if savings['validation_checks']['no_extreme_outliers'] else '✗'}
- **All Positive:** {'Yes ✓' if savings['validation_checks']['positive_savings'] else 'No ✗'}
"""
        else:
            report += f"\n**Error:** {savings['error']}\n"

        report += f"""
---

## 4. Comparable Quality Check

Analysis of {comparables['sample_size']} randomly selected properties to verify comparable matching quality.

### Statistics

- **Average Comparable Count:** {comparables['avg_comparable_count']:.1f} {'✓' if comparables['validation_checks']['avg_count_in_range'] else '✗'} (expected: 10-20)
- **Median Comparable Count:** {comparables['median_comparable_count']:.0f}
- **Range:** {comparables['min_comparable_count']} to {comparables['max_comparable_count']}
- **Average Value Similarity:** {comparables['avg_value_similarity_pct']:.1f}% within 20% of subject {'✓' if comparables['validation_checks']['similarity_reasonable'] else '✗'}

---

## 5. Edge Cases Identified

### Zero Comparables

- **Count:** {edges['zero_comparables']['count']} ({edges['zero_comparables']['percentage']:.1f}%)
- **Impact:** These properties cannot be analyzed for fairness

### Extreme Fairness Scores (0-10 or 90-100)

- **Count:** {edges['extreme_scores']['count']} ({edges['extreme_scores']['percentage']:.1f}%)
- **Examples:**
"""
        for ex in edges['extreme_scores']['examples']:
            report += f"  - Parcel: {ex['parcel_id']}, Score: {ex['score']}, Ratio: {ex['ratio']:.2%}\n"

        report += f"""
### Unusual Assessment Ratios (<10% or >30%)

- **Count:** {edges['unusual_ratios']['count']} ({edges['unusual_ratios']['percentage']:.1f}%)
- **Examples:**
"""
        for ex in edges['unusual_ratios']['examples']:
            report += f"  - Parcel: {ex['parcel_id']}, Ratio: {ex['ratio']:.2%}, Score: {ex['score']}\n"

        report += """
---

## 6. Overall Assessment

"""
        # Count passing checks
        all_checks = []
        all_checks.extend(fairness['validation_checks'].values())
        all_checks.extend(ratios['validation_checks'].values())
        if 'error' not in savings:
            all_checks.extend(savings['validation_checks'].values())
        all_checks.extend(comparables['validation_checks'].values())

        passing = sum(all_checks)
        total = len(all_checks)
        pass_rate = (passing / total * 100) if total > 0 else 0

        report += f"""
**Overall Pass Rate:** {passing}/{total} checks passed ({pass_rate:.1f}%)

"""
        if pass_rate >= 80:
            report += "**Status:** ✓ EXCELLENT - Analyzer is performing well\n"
        elif pass_rate >= 60:
            report += "**Status:** ⚠ GOOD - Minor calibration recommended\n"
        else:
            report += "**Status:** ✗ NEEDS CALIBRATION - Significant adjustments needed\n"

        report += """
---

## 7. Next Steps

1. Review calibration recommendations in `docs/calibration_recommendations.md`
2. Investigate edge cases documented in `docs/edge_cases_report.md`
3. Consider adjusting fairness score thresholds if distribution is skewed
4. Verify mill rate accuracy for savings estimates

---

*Report generated by validate_analyzer.py*
"""

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Validation report saved to {output_path}")

    def generate_edge_cases_report(self, output_path: str) -> None:
        """
        Generate detailed edge cases report.

        Args:
            output_path: Path to save the report
        """
        logger.info(f"Generating edge cases report: {output_path}")

        report = """# Edge Cases Report

This report documents unusual cases discovered during validation that may require
special handling or investigation.

---

## 1. Properties with Zero Comparables

Properties that could not find any comparable properties for fairness analysis.

"""
        if self.edge_cases['zero_comparables']:
            report += "| Parcel ID | Address | Total Value | Assessed Value | Ratio |\n"
            report += "|-----------|---------|-------------|----------------|-------|\n"
            for analysis in self.edge_cases['zero_comparables'][:20]:
                report += f"| {analysis.parcel_id} | {analysis.address[:40]} | ${analysis.total_val_dollars:,.0f} | ${analysis.assess_val_dollars:,.0f} | {analysis.current_ratio:.2%} |\n"

            if len(self.edge_cases['zero_comparables']) > 20:
                report += f"\n*... and {len(self.edge_cases['zero_comparables']) - 20} more*\n"
        else:
            report += "No properties found with zero comparables.\n"

        report += """
### Possible Causes:
- Unique property types with no similar properties
- Geographic isolation (rural areas)
- Extreme values (very high or low)
- Database matching criteria too strict

### Recommendations:
- Relax comparable matching criteria for isolated properties
- Consider expanding search radius
- Implement property type-specific comparable strategies

---

## 2. Extreme Fairness Scores (0-10 or 90-100)

Properties with extreme fairness scores indicating severe under or over-assessment.

"""
        if self.edge_cases['extreme_scores']:
            report += "| Parcel ID | Address | Score | Market Value | Median Comp Value | Comparables |\n"
            report += "|-----------|---------|-------|--------------|-------------------|-------------|\n"
            for analysis in self.edge_cases['extreme_scores'][:20]:
                report += f"| {analysis.parcel_id} | {analysis.address[:30]} | {analysis.fairness_score} | ${analysis.total_val_cents/100:,.0f} | ${analysis.median_comparable_value_cents/100:,.0f} | {analysis.comparable_count} |\n"

            if len(self.edge_cases['extreme_scores']) > 20:
                report += f"\n*... and {len(self.edge_cases['extreme_scores']) - 20} more*\n"
        else:
            report += "No properties found with extreme fairness scores.\n"

        report += """
### Analysis:
- Scores near 0: Significantly under-assessed compared to similar properties
- Scores near 100: Significantly over-assessed compared to similar properties

### Recommendations:
- Manual review of extreme cases to verify data accuracy
- Check for data entry errors in assessed or total values
- Investigate comparable quality for these properties

---

## 3. Unusual Assessment Ratios (<10% or >30%)

Properties with assessment ratios outside the typical range for Arkansas.

"""
        if self.edge_cases['unusual_ratios']:
            report += "| Parcel ID | Address | Ratio | Total Value | Assessed Value | Fairness Score |\n"
            report += "|-----------|---------|-------|-------------|----------------|----------------|\n"
            for analysis in self.edge_cases['unusual_ratios'][:20]:
                report += f"| {analysis.parcel_id} | {analysis.address[:30]} | {analysis.current_ratio:.2%} | ${analysis.total_val_dollars:,.0f} | ${analysis.assess_val_dollars:,.0f} | {analysis.fairness_score} |\n"

            if len(self.edge_cases['unusual_ratios']) > 20:
                report += f"\n*... and {len(self.edge_cases['unusual_ratios']) - 20} more*\n"
        else:
            report += "No properties found with unusual ratios.\n"

        report += """
### Analysis:
- Arkansas statutory rate is ~20% for residential properties
- Ratios significantly outside this range may indicate:
  - Data quality issues
  - Special property classifications
  - Assessment errors

### Recommendations:
- Flag these properties for manual review before including in analysis
- Verify property classification (residential, commercial, agricultural, etc.)
- Check for recent reassessments or appeals that may explain discrepancies

---

## 4. Summary

"""
        total_edge_cases = sum(len(cases) for cases in self.edge_cases.values())
        total_analyzed = len(self.analyses)
        edge_case_pct = (total_edge_cases / total_analyzed * 100) if total_analyzed > 0 else 0

        report += f"""
- **Total Properties Analyzed:** {total_analyzed}
- **Total Edge Cases:** {total_edge_cases} ({edge_case_pct:.1f}%)
- **Zero Comparables:** {len(self.edge_cases['zero_comparables'])}
- **Extreme Scores:** {len(self.edge_cases['extreme_scores'])}
- **Unusual Ratios:** {len(self.edge_cases['unusual_ratios'])}

---

*Report generated by validate_analyzer.py*
"""

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Edge cases report saved to {output_path}")

    def generate_calibration_recommendations(self, results: Dict[str, Any], output_path: str) -> None:
        """
        Generate calibration recommendations based on validation results.

        Args:
            results: Validation results dictionary
            output_path: Path to save the recommendations
        """
        logger.info(f"Generating calibration recommendations: {output_path}")

        fairness = results['fairness_distribution']
        ratios = results['assessment_ratios']
        savings = results['savings_estimates']
        comparables = results['comparable_quality']

        report = """# Calibration Recommendations

Based on the validation analysis, here are recommended adjustments to improve
the Assessment Analyzer's accuracy and reliability.

---

## 1. Fairness Score Thresholds

Current thresholds:
- Fair: 21-40
- Monitor: 41-60
- Appeal: 61-80
- Strong Appeal: 81-100

"""
        # Analyze if thresholds need adjustment
        median = fairness['median']
        if median < 25:
            report += """
### Recommendation: LOWER thresholds by 5 points

**Rationale:** Median score is below expected range (30-40), indicating scores are
systematically low. This suggests properties are generally being assessed fairly or
under-assessed.

**Proposed thresholds:**
- Fair: 16-35
- Monitor: 36-55
- Appeal: 56-75
- Strong Appeal: 76-100
"""
        elif median > 45:
            report += """
### Recommendation: RAISE thresholds by 5 points

**Rationale:** Median score is above expected range (30-40), indicating scores are
systematically high. This suggests many properties may be over-assessed.

**Proposed thresholds:**
- Fair: 26-45
- Monitor: 46-65
- Appeal: 66-85
- Strong Appeal: 86-100
"""
        else:
            report += """
### Recommendation: KEEP current thresholds

**Rationale:** Median score is within expected range (30-40). Current thresholds
are appropriate.

✓ No changes needed
"""

        report += """
---

## 2. Confidence Calculation

Current confidence calculation uses:
- Sample size (50% weight): Asymptotic to 50 points at 20 comparables
- Consistency (50% weight): Based on coefficient of variation

"""
        avg_comps = comparables.get('avg_comparable_count', 0)
        if avg_comps < 10:
            report += """
### Recommendation: RELAX comparable matching criteria

**Rationale:** Average comparable count is low (<10), reducing confidence in analyses.

**Proposed changes:**
- Increase search radius for comparable properties
- Relax value similarity threshold (e.g., 30% instead of 20%)
- Consider year-built tolerance adjustment
"""
        elif avg_comps > 20:
            report += """
### Recommendation: TIGHTEN comparable matching criteria

**Rationale:** High number of comparables may include dissimilar properties.

**Proposed changes:**
- Reduce search radius for more focused comparables
- Tighten value similarity threshold
- Add property type filtering
"""
        else:
            report += """
### Recommendation: MAINTAIN current criteria

**Rationale:** Average comparable count is within expected range (10-20).

✓ No changes needed
"""

        report += """
---

## 3. Savings Estimation Parameters

Current parameters:
- Default mill rate: 65.0
- Minimum worthwhile savings: $100/year

"""
        if 'error' not in savings:
            mean_savings = savings.get('mean_savings', 0)
            if mean_savings < 200:
                report += """
### Recommendation: VERIFY mill rate accuracy

**Rationale:** Average savings for appeal candidates is lower than expected.

**Action items:**
- Verify the 65.0 mill rate is accurate for Benton County
- Consider property-specific mill rates based on tax district
- Check if homestead exemptions should be factored in
"""
            elif mean_savings > 2000:
                report += """
### Recommendation: REVIEW high savings estimates

**Rationale:** Average savings seems high, may indicate over-estimation.

**Action items:**
- Verify mill rate is not inflated
- Check calculation methodology
- Consider capping maximum savings estimates
"""
            else:
                report += """
### Recommendation: MAINTAIN current parameters

**Rationale:** Savings estimates are within reasonable range ($200-$2,000).

✓ No changes needed
"""

        report += """
---

## 4. Comparable Matching Criteria

Current criteria (from ComparableService):
- Geographic proximity
- Similar total value
- Same property type
- Recent sales/assessments

"""
        value_sim = comparables.get('avg_value_similarity_pct', 0)
        if value_sim < 50:
            report += """
### Recommendation: TIGHTEN value similarity requirements

**Rationale:** Comparables have low value similarity to subject properties.

**Proposed changes:**
- Reduce value tolerance to ±15% instead of ±20%
- Add square footage similarity requirement
- Weight comparables by similarity score
"""
        elif value_sim > 80:
            report += """
### Recommendation: Consider RELAXING value requirements for edge cases

**Rationale:** High similarity is good, but may leave some properties without comparables.

**Proposed changes:**
- Implement tiered matching (strict first, then relaxed if needed)
- Use wider criteria for unique properties
"""
        else:
            report += """
### Recommendation: MAINTAIN current matching criteria

**Rationale:** Comparable value similarity is good (60-80% within 20%).

✓ No changes needed
"""

        report += f"""
---

## 5. Data Quality Filters

Current validation analysis identified:
- {ratios.get('outliers_low', 0) + ratios.get('outliers_high', 0)} properties with unusual assessment ratios
- {len(self.edge_cases.get('zero_comparables', []))} properties with zero comparables

### Recommendations:

1. **Pre-analysis filtering:**
   - Exclude properties with ratios <10% or >30% from automated analysis
   - Flag for manual review

2. **Property type classification:**
   - Enhance property type detection to avoid comparing residential to commercial
   - Add special handling for agricultural/exempt properties

3. **Geographic boundaries:**
   - Ensure comparable search respects jurisdiction boundaries
   - Consider subdivision/neighborhood as matching criteria

---

## 6. Implementation Priority

### High Priority (Immediate)
1. Verify and correct mill rate if needed
2. Implement data quality filters for extreme ratios

### Medium Priority (Next iteration)
1. Adjust fairness score thresholds based on median analysis
2. Refine comparable matching criteria

### Low Priority (Future enhancement)
1. Property-specific mill rates by tax district
2. Tiered comparable matching for edge cases
3. Machine learning model for comparable weighting

---

## 7. Monitoring Metrics

After implementing calibrations, monitor these metrics:

- **Fairness Score Distribution:** Should remain centered around 30-40
- **Appeal Rate:** Should stabilize around 10-15%
- **Comparable Count:** Average should be 12-18
- **Edge Case Rate:** Should decrease below 5%

Run this validation script monthly to track improvements.

---

*Report generated by validate_analyzer.py*
"""

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Calibration recommendations saved to {output_path}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Validate Assessment Analyzer against real Benton County data'
    )
    parser.add_argument(
        '--sample-size',
        type=int,
        default=500,
        help='Number of properties to sample (default: 500)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='docs',
        help='Output directory for reports (default: docs)'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("ASSESSMENT ANALYZER VALIDATION")
    print("=" * 80)
    print(f"Sample Size: {args.sample_size}")
    print(f"Output Directory: {args.output_dir}")
    print()

    try:
        # Initialize database connection
        print("Connecting to database...")
        engine = get_engine()

        # Initialize validator
        print("Initializing validator...")
        validator = AnalyzerValidator(engine, sample_size=args.sample_size)
        print()

        # Run validation
        print("Running validation suite...")
        print("This may take several minutes...")
        print()
        results = validator.run_full_validation()

        # Generate outputs
        print("\nGenerating reports...")

        histogram_path = os.path.join(args.output_dir, 'fairness_distribution.png')
        validator.generate_histogram(histogram_path)

        validation_report_path = os.path.join(args.output_dir, 'analyzer_validation_report.md')
        validator.generate_validation_report(results, validation_report_path)

        edge_cases_path = os.path.join(args.output_dir, 'edge_cases_report.md')
        validator.generate_edge_cases_report(edge_cases_path)

        calibration_path = os.path.join(args.output_dir, 'calibration_recommendations.md')
        validator.generate_calibration_recommendations(results, calibration_path)

        # Print summary
        print("\n" + "=" * 80)
        print("VALIDATION COMPLETE")
        print("=" * 80)
        print(f"\nAnalyzed {results['sample_size']} properties")
        print(f"\nReports generated:")
        print(f"  - {histogram_path}")
        print(f"  - {validation_report_path}")
        print(f"  - {edge_cases_path}")
        print(f"  - {calibration_path}")

        # Quick summary
        fairness = results['fairness_distribution']
        print(f"\nQuick Summary:")
        print(f"  Median Fairness Score: {fairness['median']:.1f}")
        print(f"  Appeal Candidates: {fairness['over_assessed_count']} ({fairness['over_assessed_pct']:.1f}%)")

        if 'error' not in results['savings_estimates']:
            savings = results['savings_estimates']
            print(f"  Mean Annual Savings: ${savings['mean_savings']:,.2f}")
            print(f"  Total Potential Savings: ${savings['total_potential']:,.2f}/year")

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
