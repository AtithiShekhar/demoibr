
# ================================
# scoring/scoring_system.py (UPDATED)
# ================================

"""
Unified Scoring System using Centralized Configuration
"""

import json
from datetime import datetime
from typing import Dict, Any


class ScoringSystem:
    """Scoring system that uses centralized configuration"""
    
    def __init__(self, output_file: str = "result.json"):
        self.output_file = output_file
        self.results = {}
    
    def add_analysis(self, analysis_name: str, data: Dict[str, Any]):
        """Add analysis results to the scoring system"""
        self.results[analysis_name] = data
    
    def save_to_json(self):
        """Save all results to JSON file"""
        output_data = {
            "analysis_timestamp": datetime.now().isoformat(),
            "analyses": self.results
        }
        
        with open(self.output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        return self.output_file

