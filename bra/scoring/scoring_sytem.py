
# ================================
# scoring/scoring_system.py
# ================================

import json
from datetime import datetime
from typing import Dict, Any, List


class ScoringSystem:
    """Scoring system that uses centralized configuration"""
    
    def __init__(self, output_file: str = "result.json"):
        self.output_file = output_file
        self.results = {}
        self.benefit_scores = []
        self.risk_scores = []
    
    def add_analysis(self, analysis_name: str, data: Dict[str, Any]):
        """Add analysis results and track benefit/risk scores"""
        self.results[analysis_name] = data
        
        # Track benefit and risk scores separately
        if isinstance(data, dict) and 'weighted_score' in data:
            score_type = data.get('score_type', '')
            weighted_score = data.get('weighted_score', 0)
            
            if score_type == 'benefit':
                self.benefit_scores.append(weighted_score)
            elif score_type == 'risk':
                self.risk_scores.append(weighted_score)
    
    def calculate_brr(self) -> Dict[str, Any]:
        """Calculate Benefit-Risk Ratio"""
        from scoring.config import ScoringConfig
        return ScoringConfig.calculate_brr(self.benefit_scores, self.risk_scores)
    
    def save_to_json(self):
        """Save all results to JSON file including BRR"""
        # Calculate BRR before saving
        brr_data = self.calculate_brr()
        
        output_data = {
            "analysis_timestamp": datetime.now().isoformat(),
            "analyses": self.results,
            "benefit_risk_ratio": brr_data
        }
        
        with open(self.output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        return self.output_file

