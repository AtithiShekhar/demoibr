"""
iBR Report Generator
Generates comprehensive Individual Benefit-Risk (iBR) Assessment reports in the exact UI format
UPDATED: Enhanced monitoring protocol with categorized symptoms and detailed lab tests
"""
from utils.gemini_patient_education import generate_gemini_monitoring_protocol
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
class IBRReportGenerator:
    """Generates iBR Assessment reports with Gemini AI integration for dynamic summaries and protocols"""
    @staticmethod
    def determine_ibr_outcome(brr: float, has_contraindication: bool, has_lt_adrs: bool, 
                             has_serious_adrs: bool, patient_has_risk_factors: bool) -> Dict[str, Any]:
        """
        Determine iBR outcome based on comprehensive analysis
        
        Returns:
            Dictionary with outcome, emoji, and rationale
        """
        # Unfavorable: Contraindicated or BRR < 2
        if has_contraindication:
            return {
                "outcome": "🔴 Unfavorable",
                "emoji": "🔴",
                "status": "Unfavorable",
                "score": brr if isinstance(brr, (int, float)) else 0
            }
        
        # Conditional: LT ADRs or (Serious ADRs + risk factors) with BRR 2-6
        if (has_lt_adrs or (has_serious_adrs and patient_has_risk_factors)) and 2 <= brr < 6:
            return {
                "outcome": "🟡 Conditional",
                "emoji": "🟡",
                "status": "Conditional",
                "score": brr if isinstance(brr, (int, float)) else 0
            }
        
        # Favorable: BRR >= 6 or (BRR >= 2 and no serious concerns)
        if brr >= 6 or (brr >= 2 and not has_lt_adrs and not (has_serious_adrs and patient_has_risk_factors)):
            return {
                "outcome": "🟢 Favorable",
                "emoji": "🟢",
                "status": "Favorable",
                "score": brr if isinstance(brr, (int, float)) else 0
            }
        
        # Default to Unfavorable for BRR < 2
        return {
            "outcome": "🔴 Unfavorable",
            "emoji": "🔴",
            "status": "Unfavorable",
            "score": brr if isinstance(brr, (int, float)) else 0
        }
    
    def generate_patient_summary_ai(self, patient_info: Dict, meds_list: List[str]) -> str:
        """Generates a professional clinical summary via Gemini API"""
        prompt = f"""
        Generate a professional clinical narrative for an iBR Report.
        Patient Data: {json.dumps(patient_info)}
        Medications Prescribed: {', '.join(meds_list)}
        
        Format: A single concise paragraph.
        Content: Mention age, gender, hospitalization reason (chief complaints), and the current treatment regimen.
        Tone: Professional medical report style.
        """
        response = self._call_gemini_api(prompt)
        return response if "Error" not in response else "Clinical summary currently unavailable."

    def generate_monitoring_protocol_ai(self, analysis_results: Dict, patient_info: Dict) -> str:
        """Generates patient-specific monitoring protocol via Gemini API"""
        prompt = f"""
        Create a patient-friendly monitoring protocol based on these findings:
        Patient: {json.dumps(patient_info)}
        Analysis: {json.dumps(analysis_results)}

        Instructions:
        1. Categorize symptoms by system (e.g., Breathing, Heart, Kidney).
        2. Tailor warnings to patient risk factors (e.g., emphasize kidney signs if the patient has renal history).
        3. List specific lab tests (KFT, LFT, CBC) and suggested frequency.
        4. Use the format: **[Category]**: [Symptoms]
        5. No preamble. Start directly with '**Monitoring Protocol**'.
        """
        response = self._call_gemini_api(prompt)
        return response if "Error" not in response else "Standard monitoring recommended. Contact provider for specific tests."    
    @staticmethod
    def generate_key_rationale(outcome_status: str, consequence_data: Dict, has_lt_adrs: bool,
                              lt_adrs_list: List, serious_adrs_list: List, is_acute: bool,
                              is_life_threatening: bool, contraindication_reason: str = None) -> str:
        """Generate key rationale based on outcome"""
        
        if outcome_status == "Favorable":
            # Determine disease characteristics
            disease_type = "acute" if is_acute else "chronic"
            severity = "life-threatening" if is_life_threatening else "non-life-threatening"
            
            return (f"Safe to Use with no major concerns, considering treatment for "
                   f"{disease_type}, {severity} disease with non-serious, milder, "
                   f"reversible side effects.")
        
        elif outcome_status == "Unfavorable":
            if contraindication_reason:
                return (f"Unsafe to Use in this patient because this product is "
                       f"contraindicated/restricted in patients with {contraindication_reason}")
            else:
                concerns = []
                if has_lt_adrs:
                    concerns.append("life-threatening ADRs")
                if serious_adrs_list:
                    concerns.append("serious ADRs")
                
                concerns_str = ", ".join(concerns) if concerns else "significant safety concerns"
                return f"Unsafe to Use with significant serious concern(s) of {concerns_str}"
        
        else:  # Conditional
            risks = []
            if has_lt_adrs:
                lt_names = [adr.get('adr_name', 'Unknown') for adr in lt_adrs_list[:3]]
                risks.extend(lt_names)
            if serious_adrs_list:
                serious_names = [adr.get('adr_name', 'Unknown') for adr in serious_adrs_list[:2]]
                risks.extend(serious_names)
            
            risks_str = ", ".join(risks) if risks else "identified ADRs"
            
            return (f"Benefit risk balance for this medicine is conditionally favorable/marginal, "
                   f"due to the serious risk(s) of {risks_str}. It remains favorable only when "
                   f"the patient follows the measures specified in monitoring protocol.")
    
    @staticmethod
    def generate_benefit_factors(medication_data: Dict, detailed_analysis: Dict) -> List[Dict[str, Any]]:
        """Generate B1-B6 benefit factors"""
        
        benefit_factors = []
        
        # B1: Regulatory Approval
        reg_data = detailed_analysis.get("regulatory_approval", {})
        cdsco_approved = reg_data.get("cdsco_approved", False)
        usfda_approved = reg_data.get("usfda_approved", False)
        drug_name = medication_data.get("medication_name", "Unknown")
        indication = medication_data.get("indication", "Unknown")
        
        if usfda_approved:
            b1_desc = (f"{drug_name} is approved for use in {indication} as per USFDA's USPI "
                      f"(United States Prescriber Information).")
        else:
            b1_desc = (f"{drug_name} is not approved for use in {indication} as per USFDA's USPI "
                      f"(United States Prescriber Information). Please review the iBR score and "
                      f"consider alternative medications that are approved by regulatory bodies "
                      f"for treating {indication}.")
        
        # B1: Regulatory Approval - Handle both nested and flat structures
        reg_score = reg_data.get("score", {})
        b1_weighted_score = reg_score.get("weighted_score", 0) if reg_score else reg_data.get("weighted_score", 0)
        
        benefit_factors.append({
            "factor": "B1",
            "description": b1_desc,
            "weighted_score": b1_weighted_score
        })
        
        # B2: Market Experience
        mme_data = detailed_analysis.get("market_experience", {})
        years_in_market = mme_data.get("years_in_market", 0)
        approval_date = mme_data.get("approval_date", "Unknown")
        
        b2_desc = (f"{drug_name} is first approved by USFDA on {approval_date}. "
                  f"{drug_name} is in the market for more than {years_in_market} years "
                  f"of post-market experience.")
        
        # Handle both nested and flat structures
        mme_score = mme_data.get("score", {})
        b2_weighted_score = mme_score.get("weighted_score", 0) if mme_score else mme_data.get("weighted_score", 0)
        
        benefit_factors.append({
            "factor": "B2",
            "description": b2_desc,
            "weighted_score": b2_weighted_score
        })
        
        # B3: Clinical Evidence
        pubmed_data = detailed_analysis.get("pubmed_evidence", {})
        rct_count = pubmed_data.get("rct_count", 0)
        
        b3_desc = (f"There are {rct_count} RCTs conducted for the evaluation of "
                  f"{drug_name} use in {indication}.")
        
        # Handle both nested and flat structures
        pubmed_score = pubmed_data.get("score", {})
        b3_weighted_score = pubmed_score.get("weighted_score", 0) if pubmed_score else pubmed_data.get("weighted_score", 0)
        
        benefit_factors.append({
            "factor": "B3",
            "description": b3_desc,
            "weighted_score": b3_weighted_score
        })
        
        # B4: Therapeutic Duplication
        dup_data = detailed_analysis.get("therapeutic_duplication", {})
        dup_status = dup_data.get("status", "not_applicable")
        
        if dup_status == "unique" or dup_status == "not_applicable":
            b4_desc = f"{drug_name} is unique with no overlap in mode of action and indication with other products in the prescription."
        elif dup_status == "some_overlap":
            b4_desc = (f"{drug_name} has some overlap in mode of action and/or indication with other "
                      f"products in the prescription. But this combination/overlap use is supported "
                      f"by guideline recommendation.")
        else:
            b4_desc = (f"__Redundant combination identified:__ Use of {drug_name} with other medications "
                      f"for the same indication/with same mechanism of action is not supported by any "
                      f"standard clinical guideline and this concomitant use may cause more risk than benefit.")
        
        # Handle both nested and flat structures
        dup_score = dup_data.get("score", {})
        b4_weighted_score = dup_score.get("weighted_score", 0) if dup_score else dup_data.get("weighted_score", 0)
        
        benefit_factors.append({
            "factor": "B4",
            "description": b4_desc,
            "weighted_score": b4_weighted_score
        })
        
        # B5: Alternatives
        alternatives_count = medication_data.get("alternatives_count", 0)
        
        if alternatives_count == 0:
            b5_desc = f"No alternative existed for this medicine."
        else:
            b5_desc = (f"There are alternative medications available with comparable or better iBR scores. "
                      f"Please review the list of {alternatives_count} alternative(s) with positive iBR score "
                      f"and favorable benefit-risk balance.")
        
        benefit_factors.append({
            "factor": "B5",
            "description": b5_desc,
            "weighted_score": 0
        })
        
        # B6: Consequences of Non-Treatment
        consequence_data = medication_data.get("consequences_data", {})
        
        if consequence_data:
            # Get first disease consequence
            first_disease = list(consequence_data.keys())[0] if consequence_data else None
            if first_disease:
                disease_info = consequence_data[first_disease]
                classifications = disease_info.get("classifications", [])
                if classifications:
                    classification = classifications[0]
                    category = classification.get("category", "Unknown severity")
                    consequences = classification.get("consequences_if_untreated", "serious complications")
                    
                    b6_desc = f"There is a possible consequence of {category.lower()}, {consequences} if left untreated."
                else:
                    b6_desc = f"There is a possible consequence of disease progression if {first_disease} is left untreated."
            else:
                b6_desc = "Treatment is necessary to prevent disease progression."
        else:
            b6_desc = "Treatment is necessary to prevent disease progression."
        
        # Get consequence score from scoring
        consequence_score_data = medication_data.get("consequence_score", {})
        
        benefit_factors.append({
            "factor": "B6",
            "description": b6_desc,
            "weighted_score": consequence_score_data.get("weighted_score", 0)
        })
        
        return benefit_factors
    
    @staticmethod
    def generate_risk_factors(medication_data: Dict, detailed_analysis: Dict, 
                            rmm_data: List[Dict]) -> List[Dict[str, Any]]:
        """Generate R1-R6 risk factors"""
        
        risk_factors = []
        drug_name = medication_data.get("medication_name", "Unknown")
        
        # R1: Contraindication
        contra_data = detailed_analysis.get("contraindication_analysis", {})
        has_contraindication = contra_data.get("contraindication_found", False)
        
        if has_contraindication:
            risk_reason = contra_data.get("reason", "contraindicated condition")
            matched_conditions = contra_data.get("matched_conditions", [])
            conditions_str = ", ".join(matched_conditions) if matched_conditions else risk_reason
            
            r1_desc = (f"Use of this {drug_name} in patients having {conditions_str}, will cause more "
                      f"risks than benefits, which is not beneficial/favorable for the patient. "
                      f"Hence, use of this medicine is restricted as per scientific evidence and "
                      f"documentation in regulatory label. Please consider alternative medicine from "
                      f"the list with positive iBR score and favorable benefit-risk balance with better safety profile.")
        else:
            r1_desc = "No contraindications found for this patient."
        
        # Handle both nested and flat structures for contraindication score
        contra_score = contra_data.get("score", {})
        r1_weighted_score = contra_score.get("weighted_score", 0) if contra_score else contra_data.get("weighted_score", 0)
        
        risk_factors.append({
            "factor": "R1",
            "description": r1_desc,
            "weighted_score": r1_weighted_score
        })
        
        # R2: Drug-Drug Interactions
        adrs_data = detailed_analysis.get("adverse_drug_reactions", {})
        interactions = adrs_data.get("drug_interactions", [])
        
        if interactions:
            interaction_details = []
            for interaction in interactions[:3]:  # Limit to first 3
                interacting_drug = interaction.get("interacting_drug", "Unknown")
                consequence = interaction.get("consequence", "Unknown consequence")
                severity = interaction.get("severity", "Unknown")
                
                interaction_details.append({
                    "drugs": f"{drug_name} + {interacting_drug}",
                    "consequence": consequence,
                    "severity": severity
                })
            
            if any(i.get("severity") in ["Contraindicated", "Life-threatening"] for i in interaction_details):
                r2_desc = (f"There are contraindicated/LT DDIs listed below, please consider removal "
                          f"of one interacting agent as appropriate.\n")
            else:
                r2_desc = (f"There are serious DDIs listed below, please consider modifying dose or "
                          f"temporary withholding of one of the interacting agent as appropriate.\n")
            
            for detail in interaction_details:
                r2_desc += f"* Name of drugs interacting: {detail['drugs']}\n"
                r2_desc += f"* Consequence: {detail['consequence']}\n"
        else:
            r2_desc = "No drug interactions found."
        
        # Get interaction score
        interaction_score_data = medication_data.get("interaction_score", {})
        
        risk_factors.append({
            "factor": "R2",
            "description": r2_desc,
            "weighted_score": interaction_score_data.get("weighted_score", 0)
        })
        
        # R3: Life-Threatening and Serious ADRs
        lt_adrs = adrs_data.get("life_threatening_adrs", [])
        serious_adrs = adrs_data.get("serious_adrs", [])
        
        r3_desc = ""
        
        if lt_adrs:
            lt_names = [adr.get("adr_name", "Unknown") for adr in lt_adrs]
            has_risk_factors = any(adr.get("patient_has_risk_factors", False) for adr in lt_adrs)
            
            if has_risk_factors:
                risk_factor_desc = "risk factors"
                r3_desc += (f"Use of this {drug_name} in patients having {risk_factor_desc}, will cause "
                           f"LT ADRs ({', '.join(lt_names)}). Below measures are recommended to follow "
                           f"by patient to prevent this ADR occurrence (refer to RMM table).\n\n")
            else:
                r3_desc += (f"Use of this {drug_name} may cause LT ADRs like {', '.join(lt_names)}. "
                           f"Below measures are recommended to follow by patient to prevent this ADR "
                           f"occurrence (refer to RMM table).\n\n")
        else:
            r3_desc += "There are no LT ADRs for this product.\n\n"
        
        if serious_adrs:
            serious_names = [adr.get("adr_name", "Unknown") for adr in serious_adrs]
            has_risk_factors = any(adr.get("patient_has_risk_factors", False) for adr in serious_adrs)
            
            if has_risk_factors:
                r3_desc += (f"Use of this {drug_name} in patients with risk factors will cause Serious ADRs "
                           f"({', '.join(serious_names)}). Monitoring measures recommended (refer to RMM table).")
            else:
                r3_desc += (f"Use of this {drug_name} may cause Serious ADRs like {', '.join(serious_names)}. "
                           f"Monitoring measures recommended (refer to RMM table).")
        else:
            r3_desc += "There are no Serious ADRs for this product."
        
        # Get LT and Serious ADR scores
        lt_adr_score_data = medication_data.get("lt_adr_score", {})
        serious_adr_score_data = medication_data.get("serious_adr_score", {})
        combined_adr_score = (lt_adr_score_data.get("weighted_score", 0) + 
                             serious_adr_score_data.get("weighted_score", 0))
        
        risk_factors.append({
            "factor": "R3",
            "description": r3_desc,
            "weighted_score": combined_adr_score
        })
        
        # R4: Preventability (from RMF analysis)
        rmf_data = medication_data.get("rmf_data", {})
        preventability_data = rmf_data.get("risk_preventability", {})
        
        if preventability_data:
            preventable_adrs = [k.split(' - ')[1] for k, v in preventability_data.items() 
                              if v.get('classification') == 'Preventable ADR']
            non_preventable_adrs = [k.split(' - ')[1] for k, v in preventability_data.items() 
                                   if v.get('classification') == 'Non-preventable ADR']
            
            if preventable_adrs:
                r4_desc = (f"These ADRs ({', '.join(preventable_adrs)}) are preventable by adhering "
                          f"to risk mitigation measures specified in this monitoring protocol.")
            elif non_preventable_adrs:
                r4_desc = (f"These ADRs ({', '.join(non_preventable_adrs)}) are partially preventable/not "
                          f"preventable by any simple measures.")
            else:
                r4_desc = "Risk preventability assessment: Standard monitoring recommended."
        else:
            r4_desc = "Risk preventability assessment: Standard monitoring recommended."
        
        risk_factors.append({
            "factor": "R4",
            "description": r4_desc,
            "weighted_score": 0  # Informational only
        })
        
        # R5: Reversibility (from RMF analysis)
        reversibility_data = rmf_data.get("risk_reversibility_risk_tolerability", {})
        
        if reversibility_data:
            reversible_adrs = [k.split(' - ')[1] for k, v in reversibility_data.items() 
                             if v.get('classification') == 'Reversible ADR']
            irreversible_adrs = [k.split(' - ')[1] for k, v in reversibility_data.items() 
                                if v.get('classification') == 'Irreversible ADR']
            
            if reversible_adrs:
                r5_desc = (f"These ADRs ({', '.join(reversible_adrs)}) can be treated by adhering to "
                          f"risk mitigation measures specified in this monitoring protocol.")
            elif irreversible_adrs:
                r5_desc = (f"These ADRs ({', '.join(irreversible_adrs)}) are irreversible and not "
                          f"treatable with any treatment.")
            else:
                r5_desc = "Risk reversibility assessment: ADRs are generally manageable."
        else:
            r5_desc = "Risk reversibility assessment: ADRs are generally manageable."
        
        risk_factors.append({
            "factor": "R5",
            "description": r5_desc,
            "weighted_score": 0  # Informational only
        })
        
        # R6: Risk Tolerability
        rmf_score_data = medication_data.get("rmf_score", {})
        mitigation_level = rmf_score_data.get("mitigation_sub_factor", "")
        indication = medication_data.get("indication", "this condition")
        
        if "Irreversible" in mitigation_level or "Non-preventable" in mitigation_level:
            r6_desc = f"These ADRs are not tolerable in the context of {indication}"
        else:
            r6_desc = f"These ADRs are tolerable in the context of {indication}"
        
        risk_factors.append({
            "factor": "R6",
            "description": r6_desc,
            "weighted_score": rmf_score_data.get("weighted_score", 0)
        })
        
        return risk_factors
    
    @classmethod
    def generate_ibr_report(cls, analysis_results: Dict, patient_info: Dict) -> Dict[str, Any]:
        """
        Generate complete iBR Report from analysis results
        
        Args:
            analysis_results: Complete analysis results from queue manager
            patient_info: Patient demographic information
            
        Returns:
            Complete iBR Report structure
        """
        # Extract patient demographics
        age = patient_info.get("age", "Unknown")
        gender = patient_info.get("gender", "Unknown")
        full_name = patient_info.get("fullName", "Unknown")
        print("calling gemini to generate response")
        summary=generate_gemini_monitoring_protocol(analysis_results=analysis_results,patient_info=patient_info)
        # Generate patient ID (initials + age)
        initials = "".join([word[0].upper() for word in full_name.split() if word])
        patient_id = f"{initials}{age}"
        
        # Get additional patient info
        smoking = patient_info.get("smoking", "No")
        alcohol = patient_info.get("alcohol", "No")
        pregnancy_status = patient_info.get("pregnancy", "Not applicable") if gender.lower() == "female" else "Not applicable"
        
        # Current date
        assessment_date = datetime.now().strftime("%d-%b-%Y")
        
        # Extract medications from results
        medication_analysis = analysis_results.get("medication_analysis", [])
        rmm_table = analysis_results.get("risk_mitigation_measures", [])
        consequences_data = analysis_results.get("consequences_of_non_treatment", {})
        
        # Process each medication
        fma_outcomes_table = []
        all_benefit_factors = []
        all_risk_factors = []
        favorable_meds = []
        conditional_meds = []
        unfavorable_meds = []
        
        for med_analysis in medication_analysis:
            medication = med_analysis.get("medication", {})
            
            # Extract key data
            drug_name = medication.get("medication_name", "Unknown")
            indication = medication.get("indication", "Unknown")
            brr_data = medication.get("benefit_risk_score", {})
            brr = float(brr_data.get("ratio_value", 0)) if brr_data.get("ratio_value") != "Infinity" else 999
            
            safety_profile = medication.get("safety_profile", {})
            has_contraindication = safety_profile.get("contraindication_detected", False)
            
            # Get ADR info
            adrs_info = medication.get("adverse_drug_reactions", {})
            has_lt_adrs = adrs_info.get("has_life_threatening", False) if adrs_info else False
            has_serious_adrs = adrs_info.get("has_serious", False) if adrs_info else False
            
            # Determine if patient has risk factors (from ADRs)
            lt_adrs_list = adrs_info.get("life_threatening_adrs", []) if adrs_info else []
            serious_adrs_list = adrs_info.get("serious_adrs", []) if adrs_info else []
            patient_has_risk_factors = any(adr.get("patient_has_risk_factors", False) 
                                          for adr in lt_adrs_list + serious_adrs_list)
            
            # Get consequence data for this indication
            is_acute = False
            is_life_threatening = False
            if consequences_data:
                for disease, data in consequences_data.items():
                    if disease.lower() in indication.lower() or indication.lower() in disease.lower():
                        classifications = data.get("classifications", [])
                        for classification in classifications:
                            category = classification.get("category", "").lower()
                            if "acute" in category:
                                is_acute = True
                            if "life-threatening" in category:
                                is_life_threatening = True
            
            # Determine iBR outcome
            outcome_data = cls.determine_ibr_outcome(
                brr, has_contraindication, has_lt_adrs, 
                has_serious_adrs, patient_has_risk_factors
            )
            
            # Get contraindication reason
            contra_data = medication.get("contraindication_analysis", {})
            contra_reason = contra_data.get("reason", "") if has_contraindication else None
            
            # Generate key rationale
            key_rationale = cls.generate_key_rationale(
                outcome_data["status"], consequences_data, has_lt_adrs,
                lt_adrs_list, serious_adrs_list, is_acute, is_life_threatening,
                contra_reason
            )
            
            # Add to FMA outcomes table
            fma_outcomes_table.append({
                "medication_name": drug_name,
                "indication": indication,
                "ibr_outcome": outcome_data["outcome"],
                "ibr_score": round(brr, 1),
                "key_rationale": key_rationale,
                "reference": "USPI"
            })
            
            # Categorize medication
            if outcome_data["status"] == "Favorable":
                favorable_meds.append(drug_name)
            elif outcome_data["status"] == "Conditional":
                conditional_meds.append({
                    "name": drug_name,
                    "indication": indication,
                    "rmm": [r for r in rmm_table if r.get("medicine", "").lower() == drug_name.lower()]
                })
            else:
                unfavorable_meds.append({
                    "name": drug_name,
                    "indication": indication,
                    "reason": key_rationale
                })
            
            # Generate benefit and risk factors
            detailed_analysis = {
                "regulatory_approval": medication.get("regulatory_approval", {}),
                "market_experience": medication.get("market_experience", {}),
                "pubmed_evidence": medication.get("pubmed_evidence", {}),
                "contraindication_analysis": medication.get("contraindication_analysis", {}),
                "therapeutic_duplication": medication.get("therapeutic_duplication", {}),
                "adverse_drug_reactions": adrs_info
            }
            
            # Add scoring data to medication_data for benefit/risk factor generation
            medication_with_scores = {
                **medication,
                "alternatives_count": med_analysis.get("alternatives_count", 0),
                "consequences_data": consequences_data,
                "consequence_score": medication.get("consequence_score", {}),
                "lt_adr_score": medication.get("lt_adr_score", {}),
                "serious_adr_score": medication.get("serious_adr_score", {}),
                "interaction_score": medication.get("interaction_score", {}),
                "rmf_score": medication.get("rmf_score", {}),
                "rmf_data": medication.get("rmf_data", {})
            }
            
            benefit_factors = cls.generate_benefit_factors(medication_with_scores, detailed_analysis)
            risk_factors = cls.generate_risk_factors(medication_with_scores, detailed_analysis, rmm_table)
            
            all_benefit_factors.append({
                "medication": drug_name,
                "factors": benefit_factors
            })
            
            all_risk_factors.append({
                "medication": drug_name,
                "factors": risk_factors
            })
        
        # Generate overall clinical recommendation
        clinical_recommendation = cls.generate_clinical_recommendation(
            favorable_meds, conditional_meds, unfavorable_meds, rmm_table
        )
        
        # Generate patient education / monitoring protocol
        monitoring_protocol = cls.generate_monitoring_protocol(rmm_table, conditional_meds)
        
        # Compile complete iBR Report
        ibr_report = {
            "report_header": {
                "title": "iBR Assessment Report",
                "subtitle": "Individual Benefit-Risk Assessment",
                "patient_id": patient_id,
                "assessment_date": assessment_date
            },
            
            "patient_demographics": {
                "age_gender": f"{age} Years, {gender}",
                "smoking_alcohol": f"Smoking: {smoking}, Alcohol: {alcohol}",
                "pregnancy_status": pregnancy_status,
                "date_of_assessment": assessment_date
            },
            
            "patient_medication_details": {
                "current_prescription": cls.format_current_prescription(medication_analysis, patient_info),
                "concurrent_medications": []  # To be populated if historical data available
            },
            
            "fma_outcomes_summary": {
                "table": fma_outcomes_table,
                "total_medications": len(fma_outcomes_table),
                "favorable_count": len(favorable_meds),
                "conditional_count": len(conditional_meds),
                "unfavorable_count": len(unfavorable_meds)
            },
            
            "benefit_factors_by_medication": all_benefit_factors,
            
            "risk_factors_by_medication": all_risk_factors,
            
            "overall_clinical_recommendation": clinical_recommendation,
            
            "patient_education": {
                "monitoring_protocol": summary,
                "rmm_table": rmm_table
            },
            
            "references": [
                "USPI (United States Prescribing Information)",
                "FDA Drug Labels and Databases",
                "PubMed Clinical Trial Database",
                "CDSCO Drug Information",
                "Clinical Practice Guidelines"
            ]
        }
        
        return ibr_report
    
    @staticmethod
    def format_current_prescription(medication_analysis: List, patient_info: Dict) -> str:
        """Format current prescription narrative"""
        
        age = patient_info.get("age", "XX")
        gender = patient_info.get("gender", "Unknown")
        
        # Extract chief complaints
        chief_complaints = patient_info.get("chiefComplaints", [])
        complaints_str = ", ".join([c.get("complaint", "") for c in chief_complaints if c.get("complaint")])
        
        # Extract medications and diagnoses
        meds_list = []
        diagnoses = set()
        
        for med_data in medication_analysis:
            medication = med_data.get("medication", {})
            drug_name = medication.get("medication_name", "Unknown")
            indication = medication.get("indication", "Unknown")
            
            meds_list.append(drug_name)
            diagnoses.add(indication)
        
        meds_str = ", ".join(meds_list)
        diagnoses_str = ", ".join(diagnoses)
        
        narrative = (f"This iBR Assessment concerns a {age}-year-old {gender} patient who was "
                    f"hospitalized for {complaints_str if complaints_str else 'medical evaluation'} "
                    f"and was prescribed with {meds_str} for treatment of {diagnoses_str}.")
        
        return narrative
    
    @classmethod
    def generate_clinical_recommendation(cls, favorable_meds: List, conditional_meds: List, 
                                        unfavorable_meds: List, rmm_table: List) -> Dict[str, Any]:
        """Generate overall clinical recommendations"""
        
        recommendations = {
            "favorable_medications": {
                "title": "Medications with Favorable Outcome",
                "description": "Positive benefit-risk profile with no concerns on patient safety impact.",
                "medications": favorable_meds,
                "action": "Continue as prescribed with standard monitoring"
            },
            
            "conditional_medications": {
                "title": "Medications with Conditional Outcome",
                "description": ("Marginal benefit-risk profile. If recommended measures are not implemented/followed, "
                              "benefit-risk profile shifts to negative end causing more harm than intended benefits."),
                "medications": [{"name": m["name"], "indication": m["indication"]} for m in conditional_meds],
                "action": "Implement strict monitoring protocol as specified in RMM table",
                "rmm_summary": cls._summarize_rmm(conditional_meds)
            },
            
            "unfavorable_medications": {
                "title": "Medications with Unfavorable Outcome",
                "description": ("Negative benefit-risk profile. Should be re-evaluated or discontinued as these "
                              "medications are either absolutely contraindicated or lack adequate risk mitigation."),
                "medications": [{"name": m["name"], "indication": m["indication"], "reason": m["reason"]} 
                              for m in unfavorable_meds],
                "action": "URGENT: Review and consider alternatives immediately"
            }
        }
        
        return recommendations
    
    @staticmethod
    def _summarize_rmm(conditional_meds: List) -> str:
        """Summarize RMM for conditional medications"""
        if not conditional_meds:
            return ""
        
        summary_parts = []
        for med in conditional_meds:
            name = med["name"]
            rmm_entries = med.get("rmm", [])
            
            if rmm_entries:
                for entry in rmm_entries:
                    symptoms = entry.get("proactive_actions_symptoms_to_monitor", "")
                    actions = entry.get("immediate_actions_required", "")
                    
                    summary_parts.append(
                        f"For {name}: Monitor for {symptoms}. {actions}"
                    )
        
        return " ".join(summary_parts)
    
    @classmethod
    def generate_monitoring_protocol(cls, rmm_table: List, conditional_meds: List) -> str:
        """Generate patient-friendly monitoring protocol in organized format"""
        
        if not rmm_table:
            return "Continue standard medication regimen as prescribed. Report any unusual symptoms to your healthcare provider."
        
        protocol = "**Monitoring Protocol**\n\n"
        protocol += "Please be aware and monitor for the following signs or symptoms and report immediately to your healthcare provider:\n\n"
        
        # Categorize symptoms by system/type
        symptom_categories = {}
        lab_tests_needed = set()
        
        for entry in rmm_table:
            adr_name = entry.get("adr_name", "")
            symptoms = entry.get("proactive_actions_symptoms_to_monitor", "")
            lab_tests = entry.get("lab_tests_required", "")
            
            if symptoms:
                # Try to categorize symptoms based on ADR name or symptoms content
                category = cls._categorize_symptoms(adr_name, symptoms)
                
                if category not in symptom_categories:
                    symptom_categories[category] = []
                
                symptom_categories[category].append(symptoms)
            
            # Extract lab tests
            if lab_tests:
                # Split by common delimiters and clean up
                tests = [t.strip() for t in lab_tests.replace(',', ';').split(';') if t.strip()]
                lab_tests_needed.update(tests)
        
        # Format symptom categories
        for category, symptoms_list in symptom_categories.items():
            # Combine and deduplicate symptoms for this category
            all_symptoms = []
            for symptoms in symptoms_list:
                # Split by common delimiters
                symptom_parts = [s.strip() for s in symptoms.replace(',', ';').split(';') if s.strip()]
                all_symptoms.extend(symptom_parts)
            
            # Remove duplicates while preserving order
            unique_symptoms = []
            seen = set()
            for symptom in all_symptoms:
                symptom_lower = symptom.lower()
                if symptom_lower not in seen:
                    seen.add(symptom_lower)
                    unique_symptoms.append(symptom)
            
            if unique_symptoms:
                protocol += f"**{category}:** {', '.join(unique_symptoms)}\n\n"
        
        # Format lab tests section
        if lab_tests_needed:
            protocol += "**Please do the following lab tests and share reports with your healthcare provider:**\n\n"
            
            # Organize lab tests by category
            lab_categories = {
                "Kidney Function Tests (KFTs)": [],
                "Liver Function Tests (LFTs)": [],
                "Blood Tests": [],
                "Other Tests": []
            }
            
            for test in sorted(lab_tests_needed):
                test_lower = test.lower()
                if any(keyword in test_lower for keyword in ['creatinine', 'urea', 'bun', 'kidney', 'kft']):
                    lab_categories["Kidney Function Tests (KFTs)"].append(test)
                elif any(keyword in test_lower for keyword in ['ast', 'alt', 'sgot', 'sgpt', 'bilirubin', 'liver', 'lft']):
                    lab_categories["Liver Function Tests (LFTs)"].append(test)
                elif any(keyword in test_lower for keyword in ['cbc', 'hemoglobin', 'wbc', 'platelet', 'blood count']):
                    lab_categories["Blood Tests"].append(test)
                else:
                    lab_categories["Other Tests"].append(test)
            
            # Print non-empty categories
            for category, tests in lab_categories.items():
                if tests:
                    protocol += f"● **{category}**\n"
                    for test in tests:
                        protocol += f"  ○ {test}\n"
            
            protocol += "\n**Frequency**\n\n"
            protocol += "● Every 2 weeks, or as advised by your doctor\n"
        else:
            # Default lab tests if none specified
            protocol += "**Please do the following lab tests and share reports with your healthcare provider:**\n\n"
            protocol += "● **Kidney Function Tests (KFTs)**\n"
            protocol += "  ○ Serum creatinine\n"
            protocol += "  ○ Blood urea\n"
            protocol += "● **Liver Function Tests (LFTs)**\n"
            protocol += "  ○ AST (SGOT), ALT (SGPT), Bilirubin\n\n"
            protocol += "**Frequency**\n\n"
            protocol += "● Every 2 weeks, or as advised by your doctor\n"
        
        return protocol
    
    @staticmethod
    def _categorize_symptoms(adr_name: str, symptoms: str) -> str:
        """Categorize symptoms based on ADR name or symptom content"""
        
        adr_lower = adr_name.lower()
        symptoms_lower = symptoms.lower()
        
        # Check for specific categories
        if any(keyword in adr_lower or keyword in symptoms_lower 
               for keyword in ['breath', 'respiratory', 'lung', 'wheez', 'chest']):
            return "Breathing Problems"
        
        if any(keyword in adr_lower or keyword in symptoms_lower 
               for keyword in ['kidney', 'renal', 'urine', 'urinary']):
            return "Urine / Kidney Problems"
        
        if any(keyword in adr_lower or keyword in symptoms_lower 
               for keyword in ['ear', 'hearing', 'tinnitus', 'ototoxic', 'dizz', 'balance']):
            return "Ear Problems"
        
        if any(keyword in adr_lower or keyword in symptoms_lower 
               for keyword in ['liver', 'hepatic', 'jaundice', 'yellow']):
            return "Liver Problems"
        
        if any(keyword in adr_lower or keyword in symptoms_lower 
               for keyword in ['heart', 'cardiac', 'arrhythmia', 'palpitation']):
            return "Heart Problems"
        
        if any(keyword in adr_lower or keyword in symptoms_lower 
               for keyword in ['skin', 'rash', 'dermat', 'itch', 'hives']):
            return "Skin Problems"
        
        if any(keyword in adr_lower or keyword in symptoms_lower 
               for keyword in ['gastro', 'stomach', 'nausea', 'vomit', 'diarrhea', 'gi']):
            return "Stomach / Digestive Problems"
        
        if any(keyword in adr_lower or keyword in symptoms_lower 
               for keyword in ['neuro', 'nerve', 'seizure', 'tremor', 'headache']):
            return "Neurological Problems"
        
        if any(keyword in adr_lower or keyword in symptoms_lower 
               for keyword in ['bleed', 'hemorrh', 'bruise', 'coagulation']):
            return "Bleeding Problems"
        
        # Default category
        return "General Warning Signs"


def format_ibr_response(analysis_results: Dict, input_data: Dict) -> Dict[str, Any]:
    """
    Main function to format analysis results into iBR Report
    
    Args:
        analysis_results: Complete analysis results from queue manager
        input_data: Original input data with patient info
        
    Returns:
        Complete iBR Report ready for UI display
    """
    patient_info = input_data.get("patientInfo", {})
    
    generator = IBRReportGenerator()
    ibr_report = generator.generate_ibr_report(analysis_results, patient_info)
    
    return ibr_report