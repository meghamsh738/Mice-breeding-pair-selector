"""
Mice Breeding Pair Selector Backend API
Extracted from the original PyQt5 application.
Handles gene database, genotype parsing, and breeder pair analysis.
"""

import io
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from itertools import product
from datetime import datetime

app = FastAPI(title="Mice Breeding Pair Selector API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== GENE DATABASE ====================

class GeneDatabase:
    def __init__(self, filename='gene_database.json'):
        self.filename = filename
        self.transgene_db = {}
        self.transgene_to_category = {}
        self.wildtype_genotype = {}
        self.load_database()
        self.create_reverse_mapping()

    def load_database(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    self.transgene_db = json.load(f)
            except Exception as e:
                print(f"Error loading gene database: {e}")
                self.transgene_db = {}
        else:
            self.transgene_db = {}

    def save_database(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.transgene_db, f, indent=4)
        except Exception as e:
            print(f"Error saving gene database: {e}")

    def create_reverse_mapping(self):
        self.transgene_to_category = {}
        self.wildtype_genotype = {}
        for category, genes in self.transgene_db.items():
            for gene in genes:
                self.transgene_to_category[gene.lower()] = category
                gene_lower = gene.lower()
                if category in ['Cre', 'Reporter']:
                    self.wildtype_genotype[gene_lower] = '-/-'
                elif category == 'Flox':
                    self.wildtype_genotype[gene_lower] = '+/+'
                else:
                    self.wildtype_genotype[gene_lower] = '+/+'

    def add_gene_class_pair(self, gene, gene_class):
        gene = gene.strip().lower()
        gene_class = gene_class.strip().title()
        if gene_class not in self.transgene_db:
            self.transgene_db[gene_class] = []
        if gene not in self.transgene_db[gene_class]:
            self.transgene_db[gene_class].append(gene)
            self.create_reverse_mapping()
            self.save_database()

gene_db = GeneDatabase()

# ==================== DATA PROCESSOR ====================

class DataProcessor:
    def __init__(self, gene_db):
        self.gene_db = gene_db

    def normalize_genotype(self, geno_str):
        alleles = str(geno_str).split('/')
        sorted_alleles = sorted(alleles, key=lambda x: x)
        return '/'.join(sorted_alleles)

    def get_alleles(self, allele_str):
        return str(allele_str).replace(' ', '').split('/')

    def compute_offspring_genotype(self, parent1, parent2):
        alleles1 = self.get_alleles(parent1)
        alleles2 = self.get_alleles(parent2)
        offspring = [self.normalize_genotype(a + '/' + b) for a in alleles1 for b in alleles2]
        return offspring

    def calculate_probability(self, offspring_genotypes, desired_geno):
        desired = self.normalize_genotype(desired_geno)
        total = len(offspring_genotypes)
        if total == 0: return 0
        desired_count = offspring_genotypes.count(desired)
        return (desired_count / total) * 100

    def calculate_similarity_score(self, offspring_genos, desired_geno):
        desired = set(self.normalize_genotype(desired_geno).split('/'))
        similarity = 0
        for geno in offspring_genos:
            offspring_set = set(geno.split('/'))
            matches = desired.intersection(offspring_set)
            similarity += len(matches)
        average_similarity = similarity / len(offspring_genos) if offspring_genos else 0
        return (average_similarity / 2) * 100

processor = DataProcessor(gene_db)

# ==================== MODELS ====================

class FindPairsRequest(BaseModel):
    breeders: List[Dict[str, Any]]
    desired_genotype: Dict[str, str]
    min_prob: float = 0.0
    use_example: bool = False


# Modernized API models for the React UI
class AnimalInput(BaseModel):
    animal_id: str
    genotype: str
    sex: str
    age: int


class DistributeRequest(BaseModel):
    animals: List[AnimalInput]
    num_groups: int
    age_leeway: int
    genotype_filter: Optional[str] = None
    use_example: bool = False


class PairRequest(BaseModel):
    animals: List[AnimalInput]
    age_leeway: int
    genotype_filter: Optional[str] = None
    use_example: bool = False

ROOT_DIR = Path(__file__).resolve().parent.parent
EXAMPLE_ANIMALS_PATH = ROOT_DIR / "example_data" / "animals.csv"

# ==================== DATA PROCESSOR ====================
ROOT_DIR = Path(__file__).resolve().parent.parent
EXAMPLE_ANIMALS_PATH = ROOT_DIR / "example_data" / "animals.csv"


def load_example_animals() -> pd.DataFrame:
    """Load the bundled example dataset for the modern UI."""
    if not EXAMPLE_ANIMALS_PATH.exists():
        raise FileNotFoundError(f"Missing example dataset at {EXAMPLE_ANIMALS_PATH}")
    df = pd.read_csv(EXAMPLE_ANIMALS_PATH)
    df.columns = [c.lower() for c in df.columns]
    return df.rename(columns={
        "animal_id": "animal_id",
        "genotype": "genotype",
        "sex": "sex",
        "age": "age"
    })


def build_animals_df(request) -> pd.DataFrame:
    """Return a DataFrame from request animals or the bundled example data."""
    if getattr(request, "use_example", False) or not getattr(request, "animals", []):
        return load_example_animals()
    animals_data = [a.dict() for a in request.animals]
    return pd.DataFrame(animals_data)


def distribute_animals(animals_df: pd.DataFrame, num_groups: int, age_leeway: int) -> List[pd.DataFrame]:
    """Distribute animals into groups, balancing genotype and sex."""
    groups: List[pd.DataFrame] = [pd.DataFrame() for _ in range(num_groups)]

    for (genotype, sex), subgroup in animals_df.groupby(['genotype', 'sex']):
        subgroup = subgroup.sort_values('age')
        for i, (_, animal) in enumerate(subgroup.iterrows()):
            group_idx = i % num_groups
            groups[group_idx] = pd.concat([groups[group_idx], animal.to_frame().T], ignore_index=True)

    return groups


def pair_animals(animals_df: pd.DataFrame, age_leeway: int) -> List[Tuple[pd.Series, pd.Series]]:
    """Pair animals based on sex, genotype, and age proximity."""
    pairs: List[Tuple[pd.Series, pd.Series]] = []
    males = animals_df[animals_df['sex'].str.upper() == 'M'].copy().sort_values('age')
    females = animals_df[animals_df['sex'].str.upper() == 'F'].copy().sort_values('age')

    used_females = set()
    for _, male in males.iterrows():
        best_match = None
        best_age_diff = float('inf')

        for idx, female in females.iterrows():
            if idx in used_females or male['genotype'] != female['genotype']:
                continue

            age_diff = abs(male['age'] - female['age'])
            if age_diff <= age_leeway and age_diff < best_age_diff:
                best_match = (idx, female)
                best_age_diff = age_diff

        if best_match:
            used_females.add(best_match[0])
            pairs.append((male, best_match[1]))

    return pairs


def load_example_breeders() -> List[Dict[str, Any]]:
    """Load breeder example dataset for parity with original PyQt app."""
    if not EXAMPLE_ANIMALS_PATH.exists():
        raise FileNotFoundError(f"Missing example dataset at {EXAMPLE_ANIMALS_PATH}")
    df = pd.read_csv(EXAMPLE_ANIMALS_PATH)
    df.columns = [c.strip().lower() for c in df.columns]
    return df.to_dict('records')

# ==================== ENDPOINTS ====================

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        all_sheets = pd.read_excel(io.BytesIO(contents), sheet_name=None, engine='openpyxl')
        
        processed_data = []
        non_gene_columns = {'breeder_name', 'gender', 'dob', 'strain', 'sheet', 'age_months', 'age', 'notes'}
        
        for sheet_name, df in all_sheets.items():
            # Standardize headers
            standardized_headers = []
            for header in df.columns:
                header_str = str(header).strip()
                header_std = header_str.lower().replace(' ', '_').replace('(', '').replace(')', '')
                
                if header_std in non_gene_columns:
                    standardized_headers.append(header_std)
                else:
                    # Gene column processing
                    if '(' in header_str and ')' in header_str:
                        gene_name, gene_class = header_str.split('(')
                        gene_name = gene_name.strip().lower().replace(' ', '_').replace('(', '').replace(')', '')
                        gene_class = gene_class.strip(')').strip().title()
                    else:
                        gene_name = header_std
                        gene_class = 'Flox'
                    
                    standardized_headers.append(gene_name)
                    gene_db.add_gene_class_pair(gene_name, gene_class)
            
            df.columns = standardized_headers
            df['sheet'] = sheet_name
            
            if 'breeder_name' in df.columns:
                # Calculate age if dob exists
                if 'dob' in df.columns:
                    today = pd.to_datetime(datetime.today().strftime('%Y-%m-%d'))
                    df['dob'] = pd.to_datetime(df['dob'], errors='coerce')
                    df['age_months'] = ((today - df['dob']).dt.days) / 30
                    # Convert timestamp to string for JSON serialization
                    df['dob'] = df['dob'].dt.strftime('%Y-%m-%d')
                
                # Replace NaN with None/Empty string
                df = df.where(pd.notnull(df), None)
                processed_data.extend(df.to_dict('records'))
                
        return {
            "success": True,
            "breeders": processed_data,
            "genes": gene_db.transgene_db
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/genes")
async def get_genes():
    return gene_db.transgene_db

@app.post("/find-pairs")
async def find_pairs(request: FindPairsRequest):
    try:
        breeders_df = pd.DataFrame(load_example_breeders() if request.use_example else request.breeders)
        desired_genotype = request.desired_genotype
        
        # Identify all relevant genes from DB
        all_genes = []
        for genes in gene_db.transgene_db.values():
            all_genes.extend(genes)
            
        direct_pairs = []
        indirect_pairs = []
        
        males = breeders_df[breeders_df['gender'].str.lower().isin(['male', 'm'])]
        females = breeders_df[breeders_df['gender'].str.lower().isin(['female', 'f'])]
        
        for idx_m, male in males.iterrows():
            for idx_f, female in females.iterrows():
                
                # Check strain compatibility
                male_strain = str(male.get('strain', '')).strip().lower()
                female_strain = str(female.get('strain', '')).strip().lower()
                same_strain = male_strain == female_strain
                
                probabilities = []
                breeder_genotypes = {'Male': {}, 'Female': {}}
                
                # Calculate for each gene
                for gene in desired_genotype.keys():
                    desired_allele = desired_genotype[gene]
                    
                    # Get parent genotypes (default to WT if missing)
                    wt = gene_db.wildtype_genotype.get(gene, '+/+')
                    p1_geno = str(male.get(gene) or wt).lower().replace(' ', '')
                    p2_geno = str(female.get(gene) or wt).lower().replace(' ', '')
                    
                    breeder_genotypes['Male'][gene] = p1_geno
                    breeder_genotypes['Female'][gene] = p2_geno
                    
                    offspring_genos = processor.compute_offspring_genotype(p1_geno, p2_geno)
                    prob = processor.calculate_probability(offspring_genos, desired_allele)
                    probabilities.append(prob)
                
                # Overall probability
                if probabilities:
                    overall_prob = 1
                    for p in probabilities:
                        overall_prob *= (p / 100)
                    overall_prob *= 100
                else:
                    overall_prob = 0
                
                pair_info = {
                    'Male': male.get('breeder_name'),
                    'Female': female.get('breeder_name'),
                    'Male_Sheet': male.get('sheet'),
                    'Female_Sheet': female.get('sheet'),
                    'Probability': round(overall_prob, 2),
                    'Same_Strain': same_strain,
                    'Breeder_Genotypes': breeder_genotypes
                }
                
                if overall_prob > request.min_prob:
                    direct_pairs.append(pair_info)
                elif overall_prob == 0:
                    # Calculate similarity for indirect pairs
                    similarity_scores = []
                    for gene in desired_genotype.keys():
                        desired_allele = desired_genotype[gene]
                        wt = gene_db.wildtype_genotype.get(gene, '+/+')
                        p1_geno = str(male.get(gene) or wt).lower().replace(' ', '')
                        p2_geno = str(female.get(gene) or wt).lower().replace(' ', '')
                        
                        offspring_genos = processor.compute_offspring_genotype(p1_geno, p2_geno)
                        sim = processor.calculate_similarity_score(offspring_genos, desired_allele)
                        similarity_scores.append(sim)
                    
                    avg_sim = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0
                    pair_info['Similarity'] = round(avg_sim, 2)
                    indirect_pairs.append(pair_info)

        # Sort results
        direct_pairs.sort(key=lambda x: x['Probability'], reverse=True)
        indirect_pairs.sort(key=lambda x: x.get('Similarity', 0), reverse=True)
        
        return {
            "direct_pairs": direct_pairs,
            "indirect_pairs": indirect_pairs
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MODERN UI ENDPOINTS ====================

@app.post("/distribute")
async def distribute_endpoint(request: DistributeRequest):
    """Distribute animals into groups for the React UI."""
    try:
        df = build_animals_df(request)

        if request.genotype_filter:
            df = df[df['genotype'] == request.genotype_filter]

        if df.empty:
            raise HTTPException(status_code=400, detail="No animals match the criteria")

        groups = distribute_animals(df, request.num_groups, request.age_leeway)
        result_groups = []
        for i, group in enumerate(groups):
            if not group.empty:
                result_groups.append({
                    "group_number": i + 1,
                    "animals": group.to_dict('records'),
                    "count": len(group)
                })

        return {
            "success": True,
            "groups": result_groups,
            "total_animals": len(df)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pair")
async def pair_endpoint(request: PairRequest):
    """Pair animals by sex, genotype, and age for the React UI."""
    try:
        df = build_animals_df(request)

        if request.genotype_filter:
            df = df[df['genotype'] == request.genotype_filter]

        if df.empty:
            raise HTTPException(status_code=400, detail="No animals match the criteria")

        pairs = pair_animals(df, request.age_leeway)
        result_pairs = []
        for male, female in pairs:
            result_pairs.append({
                "male": male.to_dict(),
                "female": female.to_dict(),
                "age_difference": abs(male['age'] - female['age'])
            })

        paired_ids = set()
        for male, female in pairs:
            paired_ids.add(male['animal_id'])
            paired_ids.add(female['animal_id'])

        unpaired = df[~df['animal_id'].isin(paired_ids)]

        return {
            "success": True,
            "pairs": result_pairs,
            "unpaired": unpaired.to_dict('records'),
            "total_pairs": len(result_pairs),
            "total_unpaired": len(unpaired)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/export-distribute")
async def export_distribute(request: DistributeRequest):
    """Export distribution results to Excel."""
    try:
        df = build_animals_df(request)

        if request.genotype_filter:
            df = df[df['genotype'] == request.genotype_filter]

        groups = distribute_animals(df, request.num_groups, request.age_leeway)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for i, group in enumerate(groups):
                if not group.empty:
                    group.to_excel(writer, sheet_name=f"Group_{i+1}", index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=animal_distribution.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/export-pairs")
async def export_pairs(request: PairRequest):
    """Export pairing results to Excel."""
    try:
        df = build_animals_df(request)

        if request.genotype_filter:
            df = df[df['genotype'] == request.genotype_filter]

        pairs = pair_animals(df, request.age_leeway)
        pairs_data = []
        for male, female in pairs:
            pairs_data.append({
                'Male_ID': male['animal_id'],
                'Male_Genotype': male['genotype'],
                'Male_Age': male['age'],
                'Female_ID': female['animal_id'],
                'Female_Genotype': female['genotype'],
                'Female_Age': female['age'],
                'Age_Difference': abs(male['age'] - female['age'])
            })

        pairs_df = pd.DataFrame(pairs_data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if not pairs_df.empty:
                pairs_df.to_excel(writer, sheet_name="Pairs", index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=animal_pairs.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/genes/add")
async def add_gene(gene: str = Form(...), gene_class: str = Form(...)):
    gene_db.add_gene_class_pair(gene, gene_class)
    return {"genes": gene_db.transgene_db}


@app.post("/genes/delete")
async def delete_genes(genes: List[str] = Form(...)):
    for g in genes:
        g_lower = g.strip().lower()
        for category, g_list in list(gene_db.transgene_db.items()):
            if g_lower in g_list:
                gene_db.transgene_db[category] = [x for x in g_list if x != g_lower]
    gene_db.create_reverse_mapping()
    gene_db.save_database()
    return {"genes": gene_db.transgene_db}


@app.post("/export-breeders")
async def export_breeders(request: FindPairsRequest):
    """Export direct/indirect breeding pairs to Excel."""
    try:
        breeders = load_example_breeders() if request.use_example or not request.breeders else request.breeders
        results = await find_pairs(FindPairsRequest(
            breeders=breeders,
            desired_genotype=request.desired_genotype,
            min_prob=request.min_prob,
            use_example=request.use_example
        ))  # type: ignore
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pd.DataFrame(results['direct_pairs']).to_excel(writer, sheet_name="Direct", index=False)
            pd.DataFrame(results['indirect_pairs']).to_excel(writer, sheet_name="Indirect", index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=breeder_pairs.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint for dev servers and E2E."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)
