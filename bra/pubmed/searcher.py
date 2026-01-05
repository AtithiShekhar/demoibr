import requests
import xml.etree.ElementTree as ET

class PubMedSearcher:
    SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(self, email=None):
        self.email = email

    def search(self, drug, condition):
        """Returns total RCT count and conclusions of top 5 studies"""
        query = f'("{drug}"[TIAB]) AND ("{condition}"[TIAB]) AND (Randomized Controlled Trial[Filter])'
        
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": 5,
            "retmode": "xml"
        }
        if self.email: params["email"] = self.email

        try:
            search_res = requests.get(self.SEARCH_URL, params=params)
            search_root = ET.fromstring(search_res.content)
            # print("the content of entire page\n")
            # print(search_res.content)
            count = int(search_root.find(".//Count").text)
            id_list = [id_node.text for id_node in search_root.findall(".//IdList/Id")]
            # print("the id list of articles is \n")
            # print(id_list)
            # 2. Fetch Conclusions for the found IDs
            conclusions = self.fetch_conclusions(id_list) if id_list else []
            
            return count, conclusions
        except Exception:
            return 0, []

    def fetch_conclusions(self, id_list):
        """Fetches abstracts and attempts to extract the conclusion section"""
        ids = ",".join(id_list)
        params = {
            "db": "pubmed",
            "id": ids,
            "retmode": "xml",
            "rettype": "abstract"
        }
        
        try:
            fetch_res = requests.get(self.FETCH_URL, params=params)
            fetch_root = ET.fromstring(fetch_res.content)
            
            results = []
            for article in fetch_root.findall(".//PubmedArticle"):
                title = article.find(".//ArticleTitle").text
                abstract_parts = article.findall(".//AbstractText")
                conclusion_text = ""
                
                for part in abstract_parts:
                    label = part.get("Label", "").upper()
                    if label in ["CONCLUSION", "CONCLUSIONS"]:
                        conclusion_text = part.text
                        break
                
       
                if not conclusion_text and abstract_parts:
                    conclusion_text = abstract_parts[-1].text
                
                if conclusion_text:
                    results.append({"title": title, "conclusion": conclusion_text})
            
            return results
        except Exception:
            return []

def format_pubmed_output(drug, condition, rct_count, conclusions):
    base_text = (f"There are {rct_count} RCTs conducted for the evaluation of "
                 f"{drug} use in {condition}.\n")
    
    if conclusions:
        base_text += "\nTop 5 Study Conclusions:\n"
        for i, study in enumerate(conclusions, 1):
            base_text += f"{i}. {study['title']}\n   Conclusion: {study['conclusion'][:300]}...\n"
    
    return base_text