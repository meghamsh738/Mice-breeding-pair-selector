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
from pydantic import BaseModel, Field
from openpyxl import load_workbook
from itertools import product
from datetime import datetime

app = FastAPI(title="Mice Breeding Pair Selector API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    # The suite loads front-ends from file:// inside Electron. Allow all origins so
    # local module windows can talk to the bundled FastAPI backend.
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== GENE DATABASE ====================

def resolve_gene_database_path(filename: str = "gene_database.json") -> Path:
    """
    Choose a writable location for persisted state.

    In the packaged Easylab Suite, module code lives under the app's resources path
    which is typically read-only. The launcher injects `EASYLAB_DATA_PATH` so the
    backend can store state (gene catalog) under Documents/Easylab/... instead.
    """
    env_path = os.environ.get("EASYLAB_DATA_PATH") or os.environ.get("EASYLAB_DATA_DIR")
    if env_path:
        base = Path(env_path)
        base.mkdir(parents=True, exist_ok=True)
        return base / filename

    # Dev / standalone fallback: store next to the modern-app root (writable).
    return Path(__file__).resolve().parent.parent / filename


class GeneDatabase:
    def __init__(self, filename: str = "gene_database.json"):
        self.path = resolve_gene_database_path(filename)
        self.transgene_db = {}
        self.transgene_to_category = {}
        self.wildtype_genotype = {}
        self.load_database()
        self.create_reverse_mapping()

    def load_database(self):
        if self.path.exists():
            try:
                with open(self.path, 'r') as f:
                    self.transgene_db = json.load(f)
            except Exception as e:
                print(f"Error loading gene database: {e}")
                self.transgene_db = {}
        else:
            self.transgene_db = {}

    def save_database(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, 'w') as f:
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
    assume_missing_wildtype: bool = False
    confirm_simple_inheritance: bool = False
    confirm_independent_assortment: bool = False
    exclude_shared_parent: bool = False
    allow_unknown_relationship: bool = False
    excluded_pairs: List[List[str]] = Field(default_factory=list)
    reviewed_results: Optional[Dict[str, Any]] = None
    review_metadata: Dict[str, Any] = Field(default_factory=dict)


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
        if (file.filename or "").lower().endswith(".csv"):
            all_sheets = {"Sheet1": pd.read_csv(io.BytesIO(contents))}
        else:
            all_sheets = pd.read_excel(io.BytesIO(contents), sheet_name=None, engine='openpyxl')
        
        processed_data = []
        non_gene_columns = {
            'breeder_name', 'breeder_id', 'animal_id', 'gender', 'dob', 'strain', 'sheet',
            'age_months', 'age', 'notes', 'sire_id', 'dam_id', 'father_id',
            'mother_id', 'parent1_id', 'parent2_id'
        }
        
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
        if request.use_example:
            breeders = load_example_breeders()
        elif request.breeders:
            breeders = request.breeders
        else:
            raise HTTPException(status_code=400, detail="Load breeder records or choose the example data before calculating pairs.")
        desired_genotype = {str(gene).strip().lower(): str(value).strip() for gene, value in request.desired_genotype.items()}
        if not desired_genotype:
            raise HTTPException(status_code=400, detail="Enter at least one target gene and genotype.")
        if not 0 <= request.min_prob <= 100:
            raise HTTPException(status_code=400, detail="Minimum probability must be between 0 and 100 percent.")

        def clean(value: Any) -> str:
            if value is None or pd.isna(value):
                return ""
            text = str(value).strip()
            return "" if text.casefold() in {"", "na", "n/a", "nan", "none", "null", "unknown", "unk", "-"} else text

        def first_text(row: Dict[str, Any], *columns: str) -> str:
            for column in columns:
                value = clean(row.get(column))
                if value:
                    return value
            return ""

        def breeder_key(breeder: Dict[str, Any], index: int) -> str:
            explicit_id = first_text(breeder, "breeder_id", "animal_id")
            if explicit_id:
                return explicit_id
            name = first_text(breeder, "breeder_name", "name")
            sheet = clean(breeder.get("sheet"))
            if not name:
                raise HTTPException(status_code=400, detail=f"Breeder row {index + 1} needs a breeder name or ID.")
            return f"{sheet}::{name}" if sheet else name

        identified = [(breeder_key(breeder, index), breeder) for index, breeder in enumerate(breeders)]
        identifiers = [key for key, _ in identified]
        if len(identifiers) != len(set(identifiers)):
            raise HTTPException(status_code=400, detail="Breeder IDs must be unique. Add a breeder_id column or distinguish names by sheet.")

        def normalized_pair_key(first: str, second: str) -> Tuple[str, str]:
            return tuple(sorted((first.strip(), second.strip())))

        excluded_keys = {
            normalized_pair_key(str(pair[0]), str(pair[1]))
            for pair in request.excluded_pairs if len(pair) == 2
        }

        males = [(key, row) for key, row in identified if clean(row.get("gender")).lower() in {"male", "m"}]
        females = [(key, row) for key, row in identified if clean(row.get("gender")).lower() in {"female", "f"}]
        direct_pairs: List[Dict[str, Any]] = []
        indirect_pairs: List[Dict[str, Any]] = []
        needs_review: List[Dict[str, Any]] = []
        excluded: List[Dict[str, Any]] = []
        below_threshold: List[Dict[str, Any]] = []

        wildtype_by_gene = {gene.lower(): value for gene, value in gene_db.wildtype_genotype.items()}
        def parent_ids(row: Dict[str, Any]) -> set[str]:
            aliases = ("sire_id", "dam_id", "father_id", "mother_id", "parent1_id", "parent2_id")
            return {clean(row.get(name)).lower() for name in aliases if clean(row.get(name))}

        def parents_complete(row: Dict[str, Any]) -> bool:
            has_sire = bool(first_text(row, "sire_id", "father_id", "parent1_id"))
            has_dam = bool(first_text(row, "dam_id", "mother_id", "parent2_id"))
            return has_sire and has_dam

        def parse_genotype(value: str) -> Optional[str]:
            cleaned = value.lower().replace(" ", "")
            alleles = cleaned.split("/")
            if len(alleles) != 2 or not all(alleles):
                return None
            return processor.normalize_genotype(cleaned)

        for gene, desired_value in desired_genotype.items():
            if parse_genotype(desired_value) is None:
                raise HTTPException(status_code=400, detail=f"Target genotype for {gene} must contain two alleles separated by '/'.")

        for male_id, male in males:
            for female_id, female in females:
                pair_id = "::".join(sorted((male_id, female_id)))
                male_strain = clean(male.get("strain")).lower()
                female_strain = clean(female.get("strain")).lower()
                pair_info: Dict[str, Any] = {
                    "Pair_ID": pair_id,
                    "Male_ID": male_id,
                    "Female_ID": female_id,
                    "Male": first_text(male, "breeder_name", "name") or male_id,
                    "Female": first_text(female, "breeder_name", "name") or female_id,
                    "Male_Sheet": clean(male.get("sheet")),
                    "Female_Sheet": clean(female.get("sheet")),
                    "Same_Strain": bool(male_strain and female_strain and male_strain == female_strain),
                    "Breeder_Genotypes": {"Male": {}, "Female": {}},
                    "Locus_Probabilities": {},
                    "Reasons": [],
                    "Status": "Eligible",
                }

                if normalized_pair_key(male_id, female_id) in excluded_keys:
                    pair_info.update(Status="Excluded", Reasons=["Pair excluded by the researcher."])
                    excluded.append(pair_info)
                    continue

                shared_parents = sorted(parent_ids(male) & parent_ids(female))
                relationship_unknown = not (parents_complete(male) and parents_complete(female))
                pair_info["Relationship"] = "Shared parent" if shared_parents else "Unresolved" if relationship_unknown else "No shared parent identified"
                pair_info["Shared_Parent_IDs"] = shared_parents
                if request.exclude_shared_parent and shared_parents:
                    pair_info.update(Status="Excluded", Reasons=["The breeders have a known shared parent."])
                    excluded.append(pair_info)
                    continue
                if request.exclude_shared_parent and relationship_unknown and not request.allow_unknown_relationship:
                    pair_info.update(Status="Needs review", Reasons=["One or both breeders have incomplete parent IDs."])
                    needs_review.append(pair_info)
                    continue
                if request.exclude_shared_parent and relationship_unknown:
                    pair_info["Reasons"].append("Parent IDs are incomplete. This pair was retained after your confirmation.")

                locus_probabilities: List[float] = []
                missing_genotypes: List[str] = []
                invalid_genotypes: List[str] = []
                assumptions: List[str] = []
                for gene, desired_value in desired_genotype.items():
                    target = parse_genotype(desired_value)

                    parent_genotypes: Dict[str, Optional[str]] = {}
                    for sex, row, breeder_id in (("Male", male, male_id), ("Female", female, female_id)):
                        raw = clean(row.get(gene))
                        if not raw and request.assume_missing_wildtype:
                            raw = clean(wildtype_by_gene.get(gene))
                            if raw:
                                animal_name = first_text(row, "breeder_name", "name") or breeder_id
                                assumptions.append(f"{sex} {animal_name}: blank {gene} treated as {raw}.")
                        parsed = parse_genotype(raw) if raw else None
                        parent_genotypes[sex] = parsed
                        pair_info["Breeder_Genotypes"][sex][gene] = parsed or raw
                        if not raw:
                            missing_genotypes.append(f"{sex} {gene}")
                        elif parsed is None:
                            invalid_genotypes.append(f"{sex} {gene}")

                    if request.confirm_simple_inheritance and parent_genotypes["Male"] is not None and parent_genotypes["Female"] is not None:
                        offspring = processor.compute_offspring_genotype(parent_genotypes["Male"], parent_genotypes["Female"])
                        probability = processor.calculate_probability(offspring, target)
                        pair_info["Locus_Probabilities"][gene] = round(probability, 2)
                        locus_probabilities.append(probability)

                pair_info["Assumptions"] = assumptions
                if missing_genotypes or invalid_genotypes:
                    reasons = []
                    if missing_genotypes:
                        reasons.append("Missing genotypes: " + ", ".join(missing_genotypes) + ".")
                    if invalid_genotypes:
                        reasons.append("Check genotype format: " + ", ".join(invalid_genotypes) + ".")
                    pair_info.update(Status="Needs review", Reasons=reasons)
                    needs_review.append(pair_info)
                    continue

                if not request.confirm_simple_inheritance:
                    pair_info.update(Status="Needs review", Reasons=["Confirm the simple two-allele inheritance model before viewing genotype probabilities."])
                    needs_review.append(pair_info)
                    continue

                if len(locus_probabilities) > 1 and request.confirm_independent_assortment:
                    combined_probability = 100.0
                    for probability in locus_probabilities:
                        combined_probability *= probability / 100.0
                    pair_info["Probability"] = round(combined_probability, 2)
                    pair_info["Rank_Basis"] = "Combined probability under the confirmed independent-assortment assumption"
                    rank_score = combined_probability
                elif len(locus_probabilities) > 1:
                    pair_info["Probability"] = None
                    pair_info["Rank_Basis"] = "Lowest per-locus probability; combined probability not calculated"
                    rank_score = min(locus_probabilities)
                else:
                    pair_info["Probability"] = round(locus_probabilities[0], 2) if locus_probabilities else None
                    pair_info["Rank_Basis"] = "Single-locus probability"
                    rank_score = locus_probabilities[0] if locus_probabilities else 0

                pair_info["Ranking_Score"] = round(rank_score, 2)
                if locus_probabilities and all(probability > 0 for probability in locus_probabilities):
                    if rank_score >= request.min_prob:
                        direct_pairs.append(pair_info)
                    else:
                        pair_info.update(Status="Below threshold", Reasons=[f"Ranking score is below the {request.min_prob:g}% minimum."])
                        below_threshold.append(pair_info)
                else:
                    similarity_scores = []
                    for gene, probability in pair_info["Locus_Probabilities"].items():
                        if probability == 0:
                            desired = desired_genotype[gene]
                            male_genotype = pair_info["Breeder_Genotypes"]["Male"][gene]
                            female_genotype = pair_info["Breeder_Genotypes"]["Female"][gene]
                            offspring = processor.compute_offspring_genotype(male_genotype, female_genotype)
                            similarity_scores.append(processor.calculate_similarity_score(offspring, desired))
                    pair_info["Similarity"] = round(sum(similarity_scores) / len(similarity_scores), 2) if similarity_scores else 0
                    indirect_pairs.append(pair_info)

        sort_score = lambda row: (row.get("Ranking_Score") or 0, row["Male_ID"], row["Female_ID"])
        direct_pairs.sort(key=sort_score, reverse=True)
        indirect_pairs.sort(key=lambda row: (row.get("Similarity") or 0, *sort_score(row)), reverse=True)

        return {
            "algorithm_version": "breeding-review-v2",
            "direct_pairs": direct_pairs,
            "indirect_pairs": indirect_pairs,
            "needs_review_pairs": needs_review,
            "excluded_pairs": excluded,
            "below_threshold_pairs": below_threshold,
            "probability_method": (
                "Inheritance model not confirmed"
                if not request.confirm_simple_inheritance
                else
                "Independent assortment confirmed"
                if len(desired_genotype) > 1 and request.confirm_independent_assortment
                else "Per-locus probabilities; combined probability not calculated"
                if len(desired_genotype) > 1
                else "Single-locus probability"
            ),
            "assumptions": {
                "missing_wildtype_confirmed": request.assume_missing_wildtype,
                "simple_inheritance_confirmed": request.confirm_simple_inheritance,
                "independent_assortment_confirmed": len(desired_genotype) > 1 and request.confirm_simple_inheritance and request.confirm_independent_assortment,
                "shared_parent_exclusion_enabled": request.exclude_shared_parent,
                "unknown_parent_records_allowed": request.allow_unknown_relationship,
            },
        }
        
    except HTTPException:
        raise
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
        results = request.reviewed_results
        if results is None:
            breeders = request.breeders
            results = await find_pairs(FindPairsRequest(
                breeders=breeders,
                desired_genotype=request.desired_genotype,
                min_prob=request.min_prob,
                use_example=request.use_example,
                assume_missing_wildtype=request.assume_missing_wildtype,
                confirm_simple_inheritance=request.confirm_simple_inheritance,
                confirm_independent_assortment=request.confirm_independent_assortment,
                exclude_shared_parent=request.exclude_shared_parent,
                allow_unknown_relationship=request.allow_unknown_relationship,
                excluded_pairs=request.excluded_pairs,
            ))  # type: ignore
        direct_pairs = results.get("direct_pairs", [])
        selected_pair_id = str(request.review_metadata.get("selected_pair_id", "")).strip()
        locked_pair_id = str(request.review_metadata.get("locked_pair_id", "")).strip()
        selection_reason = str(request.review_metadata.get("selection_reason", "")).strip()
        selected_pair_index = next(
            (index for index, pair in enumerate(direct_pairs) if pair.get("Pair_ID") == selected_pair_id),
            None,
        ) if selected_pair_id else None
        if selected_pair_id and selected_pair_index is None:
            raise HTTPException(status_code=400, detail="Only pairs that can produce the target at each locus can be selected.")
        if locked_pair_id and locked_pair_id != selected_pair_id:
            raise HTTPException(status_code=400, detail="The locked pair must match the selected eligible pair.")
        if selected_pair_index is not None and selected_pair_index > 0 and not selection_reason:
            raise HTTPException(status_code=400, detail="Add a reason when choosing a different eligible pair.")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pd.DataFrame(results['direct_pairs']).to_excel(writer, sheet_name="Direct", index=False)
            pd.DataFrame(results['indirect_pairs']).to_excel(writer, sheet_name="Indirect", index=False)
            pd.DataFrame(results.get('needs_review_pairs', [])).to_excel(writer, sheet_name="Needs review", index=False)
            pd.DataFrame(results.get('excluded_pairs', [])).to_excel(writer, sheet_name="Excluded", index=False)
            pd.DataFrame(results.get('below_threshold_pairs', [])).to_excel(writer, sheet_name="Below threshold", index=False)
            input_rows = request.breeders or (load_example_breeders() if request.use_example else [])
            pd.DataFrame(input_rows).to_excel(writer, sheet_name="Breeder inputs", index=False)
            selected_pairs = [
                pair for pair in direct_pairs
                if pair.get("Pair_ID") == selected_pair_id
            ]
            pd.DataFrame(selected_pairs).to_excel(writer, sheet_name="Selected pair", index=False)
            review_rows = [
                {"Setting": "Target genotype", "Value": json.dumps(request.review_metadata.get("target_genotype", request.desired_genotype), sort_keys=True)},
                {"Setting": "Probability method", "Value": results.get("probability_method", "")},
                {"Setting": "Algorithm version", "Value": results.get("algorithm_version", "")},
                {"Setting": "Selected pair ID", "Value": request.review_metadata.get("selected_pair_id", "")},
                {"Setting": "Selection reason", "Value": request.review_metadata.get("selection_reason", "")},
                {"Setting": "Locked pair ID", "Value": request.review_metadata.get("locked_pair_id", "")},
                {"Setting": "Confirmed assumptions", "Value": json.dumps(results.get("assumptions", {}), sort_keys=True)},
                {"Setting": "Specific pair exclusions", "Value": json.dumps(request.review_metadata.get("excluded_pairs", request.excluded_pairs))},
                {"Setting": "Selected pair was locked", "Value": bool(request.review_metadata.get("locked_pair_id"))},
                {"Setting": "Exported at", "Value": request.review_metadata.get("saved_at", "")},
            ]
            pd.DataFrame(review_rows).to_excel(writer, sheet_name="Review", index=False)
        output.seek(0)
        workbook = load_workbook(output)
        for worksheet in workbook.worksheets:
            for row in worksheet.iter_rows():
                for cell in row:
                    if cell.data_type == "f":
                        cell.data_type = "s"
        safe_output = io.BytesIO()
        workbook.save(safe_output)
        safe_output.seek(0)
        return StreamingResponse(
            safe_output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=breeder_pairs.xlsx"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint for dev servers and E2E."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)
