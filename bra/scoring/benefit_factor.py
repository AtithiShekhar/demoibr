"""
scoring/benefit_factor.py
Benefit Factor Scoring System for Drug Indication Analysis
"""

from typing import Dict, Tuple


class BenefitFactorScorer:
    """Calculate benefit factor scores based on regulatory approval"""
    
    # Weights for different approval scenarios
    WEIGHTS = {
        'both_approved': 90,      # CDSCO + USFDA approved
        'single_approved': 50,    # Only one approved
        'off_label': 10          # Neither approved
    }
    
    # Scores for different approval scenarios
    SCORES = {
        'both_approved': 4,       # Both approved
        'cdsco_only': 3,         # CDSCO approved only
        'usfda_only': 3,         # USFDA approved only
        'off_label': 1           # Neither approved
    }
    
    def calculate_score(self, cdsco_approved: bool, usfda_approved: bool) -> Dict:
        """
        Calculate benefit factor weight and score
        
        Args:
            cdsco_approved: Whether approved by CDSCO
            usfda_approved: Whether approved by USFDA
            
        Returns:
            Dictionary with benefit_type, weight, score, and weighted_score
        """
        # Determine benefit type and assign weight/score
        if cdsco_approved and usfda_approved:
            benefit_type = "Approved Use"
            weight = self.WEIGHTS['both_approved']
            score = self.SCORES['both_approved']
        elif cdsco_approved:
            benefit_type = "Approved Use (CDSCO only)"
            weight = self.WEIGHTS['single_approved']
            score = self.SCORES['cdsco_only']
        elif usfda_approved:
            benefit_type = "Approved Use (USFDA only)"
            weight = self.WEIGHTS['single_approved']
            score = self.SCORES['usfda_only']
        else:
            benefit_type = "Off label"
            weight = self.WEIGHTS['off_label']
            score = self.SCORES['off_label']
        
        # Calculate weighted score (Weight × Score)
        weighted_score = weight * score
        
        return {
            'benefit_type': benefit_type,
            'weight': weight,
            'score': score,
            'weighted_score': weighted_score,
            'cdsco_approved': cdsco_approved,
            'usfda_approved': usfda_approved
        }
    
    def format_output_table(self, result: Dict) -> str:
        """
        Format output as a table
        
        Args:
            result: Result dictionary from calculate_score()
            
        Returns:
            Formatted table string
        """
        benefit_type = result['benefit_type']
        weight = result['weight']
        score = result['score']
        weighted_score = result['weighted_score']
        
        # Simplify benefit type for display
        display_type = "Approved Use" if "Approved Use" in benefit_type else "Off label"
        
        output = []
        output.append("Benefit Sub-Factor\tWeight (10–100)\tScore (1–5)\tWeighted Score")
        output.append(f"{display_type}\t\t{weight}\t\t{score}\t\t{weighted_score}")
        
        return "\n".join(output)
    
    def format_output_simple(self, result: Dict) -> str:
        """
        Format output in simple format (one value per line)
        
        Args:
            result: Result dictionary from calculate_score()
            
        Returns:
            Simple formatted string
        """
        benefit_type = result['benefit_type']
        weight = result['weight']
        score = result['score']
        weighted_score = result['weighted_score']
        
        # Simplify benefit type for display
        display_type = "Approved Use" if "Approved Use" in benefit_type else "Off label"
        
        return f"{display_type}\n{weight}\n{score}\n{weighted_score}"
    
    def format_output_detailed(self, result: Dict) -> str:
        """
        Format output with detailed explanation
        
        Args:
            result: Result dictionary from calculate_score()
            
        Returns:
            Detailed formatted string
        """
        benefit_type = result['benefit_type']
        weight = result['weight']
        score = result['score']
        weighted_score = result['weighted_score']
        cdsco = result['cdsco_approved']
        usfda = result['usfda_approved']
        
        # Simplify benefit type for display
        display_type = "Approved Use" if "Approved Use" in benefit_type else "Off label"
        
        output = []
        output.append("Benefit Sub-Factor\tWeight (10–100)\tScore (1–5)\tWeighted Score")
        output.append(f"{display_type}\t\t{weight}\t\t{score}\t\t{weighted_score}")
        output.append("")
        output.append("Calculation:")
        output.append(f"  Weighted Score = Weight × Score = {weight} × {score} = {weighted_score}")
        output.append("")
        output.append("Regulatory Status:")
        output.append(f"  CDSCO Approved: {'Yes' if cdsco else 'No'}")
        output.append(f"  USFDA Approved: {'Yes' if usfda else 'No'}")
        
        return "\n".join(output)


def format_benefit_score(cdsco_approved: bool, usfda_approved: bool, format_type: str = "table") -> str:
    """
    Main function to format benefit factor score
    
    Args:
        cdsco_approved: Whether approved by CDSCO
        usfda_approved: Whether approved by USFDA
        format_type: "table", "simple", or "detailed"
        
    Returns:
        Formatted output string
    """
    scorer = BenefitFactorScorer()
    result = scorer.calculate_score(cdsco_approved, usfda_approved)
    
    if format_type == "simple":
        return scorer.format_output_simple(result)
    elif format_type == "detailed":
        return scorer.format_output_detailed(result)
    else:
        return scorer.format_output_table(result)


def get_benefit_factor_data(cdsco_approved: bool, usfda_approved: bool) -> Dict:
    """
    Get benefit factor data for use in other calculations
    
    Returns:
        Dictionary with weight, score, and weighted_score
    """
    scorer = BenefitFactorScorer()
    return scorer.calculate_score(cdsco_approved, usfda_approved)


# Example usage
if __name__ == "__main__":
    print("="*80)
    print("BENEFIT FACTOR SCORING EXAMPLES")
    print("="*80)
    
    # Example 1: Both approved
    print("\n--- Example 1: Both CDSCO and USFDA Approved ---")
    print(format_benefit_score(cdsco_approved=True, usfda_approved=True))
    
    # Example 2: Off-label
    print("\n--- Example 2: Off-label (Neither Approved) ---")
    print(format_benefit_score(cdsco_approved=False, usfda_approved=False))
    
    # Example 3: Detailed format
    print("\n--- Example 3: Detailed Format (Both Approved) ---")
    print(format_benefit_score(cdsco_approved=True, usfda_approved=True, format_type="detailed"))