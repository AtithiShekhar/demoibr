
# this content should be fetched from chroma db , chroma db as a tool  , react pattern for agent 
DRUG_DATA = {}

# 1. Diclofenac
DRUG_DATA["diclofenac"] = {
    "name": "Diclofenac (Zorvolex)",
    "indication": [
        "Management of mild to moderate acute pain",
        "Management of osteoarthritis pain"
    ],
    "benefits": [
        "Provides analgesic and anti-inflammatory effects",
        "Useful for musculoskeletal and osteoarthritis-related pain",
        "Rapid onset of action in acute pain conditions"
    ],
    "risks": [
        "Increased risk of serious cardiovascular thrombotic events including MI and stroke",
        "Increased GI bleeding, ulceration, perforation",
        "Hepatotoxicity (elevated liver enzymes, rare hepatic failure)",
        "Hypertension, heart failure worsening",
        "Renal toxicity and hyperkalemia",
        "Anaphylactic reactions",
        "Severe skin reactions (SJS/TEN)"
    ],
    "contraindications": [
        "Hypersensitivity to diclofenac",
        "Aspirin-sensitive asthma",
        "Peri-operative period of CABG surgery"
    ],
    "interactions": [
        "Warfarin → bleeding risk",
        "SSRIs/SNRIs → bleeding",
        "ACE inhibitors/ARBs → renal risk",
        "Digoxin → increased levels",
        "Lithium → toxicity",
        "Methotrexate → toxicity",
        "Cyclosporine → nephrotoxicity",
        "Other NSAIDs",
        "CYP2C9 inhibitors/inducers"
    ],
    "rmm": [
        "Use lowest effective dose",
        "Monitor renal and liver function",
        "Monitor BP",
        "Avoid NSAID combinations",
        "Avoid after 30 weeks pregnancy"
    ],
    "monitoring": [
        "SCr, BUN",
        "LFTs",
        "CBC",
        "Blood pressure",
        "GI bleeding signs"
    ],
    "fit_med_outcome": "Conditional"
}

# 2. Amlodipine
# ------------------------------------------------------
DRUG_DATA["amlodipine"] = {
    "name": "Amlodipine",
    "indication": [
        "Hypertension",
        "Chronic stable angina",
        "Vasospastic angina",
        "Coronary artery disease with angina reduction"
    ],
    "benefits": [
        "Reduces blood pressure",
        "Reduces myocardial oxygen demand",
        "Prevents vasospasm",
        "Improves exercise tolerance"
    ],
    "risks": [
        "Hypotension",
        "Worsening angina early in therapy (rare)",
        "Peripheral edema",
        "Headache, flushing, dizziness"
    ],
    "contraindications": [
        "Hypersensitivity"
    ],
    "interactions": [
        "CYP3A4 inhibitors increase exposure",
        "CYP3A4 inducers decrease exposure"
    ],
    "rmm": [
        "Start low in elderly/liver impairment",
        "Monitor for edema",
        "Monitor for worsening angina"
    ],
    "monitoring": [
        "Blood pressure",
        "Heart rate",
        "Edema"
    ],
    "fit_med_outcome": "Favorable"
}

# ------------------------------------------------------
# 3. Atorvastatin
# ------------------------------------------------------
DRUG_DATA["atorvastatin"] = {
    "name": "Atorvastatin",
    "indication": [
        "Reduced risk of MI, stroke",
        "Hyperlipidemia",
        "Mixed dyslipidemia",
        "Familial hypercholesterolemia"
    ],
    "benefits": [
        "Strong LDL-C reduction",
        "Reduces cardiovascular events"
    ],
    "risks": [
        "Myopathy, rhabdomyolysis",
        "Hepatic enzyme elevation",
        "Small increase in glucose",
        "Immune-mediated necrotizing myopathy"
    ],
    "contraindications": [
        "Active liver disease",
        "Unexplained transaminase elevation"
    ],
    "interactions": [
        "CYP3A4 inhibitors → toxicity",
        "Cyclosporine → rhabdomyolysis",
        "Gemfibrozil → rhabdomyolysis",
        "Niacin → myopathy"
    ],
    "rmm": [
        "Check LFTs",
        "Check CK if muscle symptoms",
        "Avoid strong inhibitors"
    ],
    "monitoring": [
        "LFTs",
        "CK (if needed)",
        "Lipid panel"
    ],
    "fit_med_outcome": "Conditional"
}

# ------------------------------------------------------
# 4. Bactrim
# ------------------------------------------------------
DRUG_DATA["bactrim"] = {
    "name": "Trimethoprim–Sulfamethoxazole (Bactrim)",
    "indication": [
        "UTIs",
        "Otitis media",
        "Bronchitis exacerbations",
        "Shigellosis",
        "PJP treatment and prophylaxis"
    ],
    "benefits": [
        "Broad-spectrum activity",
        "Effective for UTIs and PJP"
    ],
    "risks": [
        "Severe hypersensitivity (SJS/TEN)",
        "Aplastic anemia, cytopenias",
        "Hyperkalemia",
        "Hepatotoxicity",
        "Nephritis"
    ],
    "contraindications": [
        "Sulfa allergy",
        "Severe liver disease",
        "Neonates"
    ],
    "interactions": [
        "Warfarin → ↑ INR",
        "ACE inhibitors → hyperkalemia",
        "Cyclosporine → nephrotoxicity"
    ],
    "rmm": [
        "Stop at first sign of rash",
        "Monitor CBC, renal function, electrolytes"
    ],
    "monitoring": [
        "CBC",
        "Electrolytes (K+)",
        "Renal function"
    ],
    "fit_med_outcome": "Conditional"
}

# ------------------------------------------------------
# 5. Aztreonam
# ------------------------------------------------------
DRUG_DATA["aztreonam"] = {
    "name": "Aztreonam (Azactam)",
    "indication": [
        "Serious Gram-negative infections"
    ],
    "benefits": [
        "Useful in beta-lactam allergy",
        "Covers Pseudomonas"
    ],
    "risks": [
        "Hypersensitivity",
        "C. difficile",
        "Hepatic enzyme elevation",
        "Cytopenias"
    ],
    "contraindications": [
        "Hypersensitivity"
    ],
    "interactions": [
        "Aminoglycosides → nephrotoxicity"
    ],
    "rmm": [
        "Dose adjust in renal failure",
        "Monitor for C. diff"
    ],
    "monitoring": [
        "Renal function",
        "CBC"
    ],
    "fit_med_outcome": "Conditional"
}

# ------------------------------------------------------
# 6. Clopidogrel
# ------------------------------------------------------
DRUG_DATA["clopidogrel"] = {
    "name": "Clopidogrel",
    "indication": [
        "Prevention of MI, stroke, PAD events",
        "ACS with aspirin"
    ],
    "benefits": [
        "Strong antiplatelet effect",
        "Prevents thrombosis"
    ],
    "risks": [
        "Bleeding",
        "TTP",
        "Hypersensitivity"
    ],
    "contraindications": [
        "Active bleeding"
    ],
    "interactions": [
        "PPIs (omeprazole) reduce effect",
        "Anticoagulants → bleeding risk"
    ],
    "rmm": [
        "Avoid CYP2C19 inhibitors",
        "Monitor bleeding"
    ],
    "monitoring": [
        "CBC",
        "Bleeding signs"
    ],
    "fit_med_outcome": "Conditional"
}

# ===================================================================
# ===================== NEW DRUGS BELOW =============================
# ===================================================================

# ------------------------------------------------------
# 7. Meropenem
# ------------------------------------------------------
DRUG_DATA["meropenem"] = {
    "name": "Meropenem",
    "indication": [
        "Febrile neutropenia",
        "Complicated intra-abdominal infections",
        "Complicated skin infections",
        "Meningitis"
    ],
    "benefits": [
        "Broad-spectrum carbapenem",
        "Excellent Gram-negative and Pseudomonas coverage"
    ],
    "risks": [
        "Seizures (especially renal impairment)",
        "Allergic reactions",
        "C. difficile"
    ],
    "contraindications": [
        "Carbapenem allergy"
    ],
    "interactions": [
        "Valproate → ↓ levels → seizures"
    ],
    "rmm": [
        "Renal dose adjustment",
        "De-escalation when cultures available"
    ],
    "monitoring": [
        "Renal function",
        "Neurological status"
    ],
    "fit_med_outcome": "Favorable"
}

# ------------------------------------------------------
# 8. Fluconazole
# ------------------------------------------------------
DRUG_DATA["fluconazole"] = {
    "name": "Fluconazole",
    "indication": [
        "Candida infections",
        "Antifungal prophylaxis post-transplant"
    ],
    "benefits": [
        "Strong Candida activity",
        "Convenient once-daily dosing"
    ],
    "risks": [
        "Hepatotoxicity",
        "QT prolongation",
        "Raises levels of many drugs"
    ],
    "contraindications": [
        "Hypersensitivity"
    ],
    "interactions": [
        "Cyclosporine → ↑ levels",
        "Amiodarone → ↑ QT"
    ],
    "rmm": [
        "Monitor LFTs",
        "ECG monitoring if QT risk"
    ],
    "monitoring": [
        "LFTs",
        "Renal function"
    ],
    "fit_med_outcome": "Conditional"
}

# ------------------------------------------------------
# 9. Zavicefta (Ceftazidime–Avibactam)
# ------------------------------------------------------
DRUG_DATA["zavicefta"] = {
    "name": "Ceftazidime–Avibactam (Zavicefta)",
    "indication": [
        "MDR Gram-negative infections"
    ],
    "benefits": [
        "Covers KPC/OXA producers",
        "Strong Gram-negative activity"
    ],
    "risks": [
        "Nephrotoxicity",
        "C. difficile"
    ],
    "contraindications": [
        "Cephalosporin allergy"
    ],
    "interactions": [
        "Aminoglycosides → nephrotoxicity"
    ],
    "rmm": [
        "Use only when MDR suspected/confirmed",
        "Renal dose adjustment"
    ],
    "monitoring": [
        "Renal function",
        "WBC"
    ],
    "fit_med_outcome": "Unfavorable"
}

# ------------------------------------------------------
# 10. Valacyclovir
# ------------------------------------------------------
DRUG_DATA["valacyclovir"] = {
    "name": "Valacyclovir",
    "indication": [
        "HSV prophylaxis",
        "VZV prophylaxis"
    ],
    "benefits": [
        "Prevents viral reactivation",
        "Good bioavailability"
    ],
    "risks": [
        "Renal toxicity",
        "Neurotoxicity"
    ],
    "contraindications": [
        "Hypersensitivity"
    ],
    "interactions": [
        "Nephrotoxic drugs → ↑ risk"
    ],
    "rmm": [
        "Adjust dose in renal impairment"
    ],
    "monitoring": [
        "Renal function"
    ],
    "fit_med_outcome": "Favorable"
}

# ------------------------------------------------------
# 11. Cyclosporine
# ------------------------------------------------------
DRUG_DATA["cyclosporine"] = {
    "name": "Cyclosporine",
    "indication": [
        "GVHD prophylaxis",
        "Transplant immunosuppression"
    ],
    "benefits": [
        "Prevents GVHD"
    ],
    "risks": [
        "Nephrotoxicity",
        "Hypertension",
        "Drug interactions"
    ],
    "contraindications": [
        "Hypersensitivity"
    ],
    "interactions": [
        "Azoles → ↑ levels",
        "Macrolides → ↑ levels",
        "Amiodarone → ↑ toxicity"
    ],
    "rmm": [
        "Therapeutic drug monitoring required"
    ],
    "monitoring": [
        "Trough levels",
        "Renal function",
        "Blood pressure"
    ],
    "fit_med_outcome": "Conditional"
}


# Access function
def get_drug_info(name: str):
    if not name:
        return None
    return DRUG_DATA.get(name.strip().lower())
