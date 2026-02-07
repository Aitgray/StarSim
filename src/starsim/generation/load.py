from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Any, Union
import yaml

from ..core.ids import CommodityId


class GenerationSchemaError(Exception):
    """Custom exception for schema validation errors."""
    pass


def _process_weights_for_random_selection(weighted_choices: List[Dict[str, Any]]) -> tuple[List[Any], List[Union[int, float]]]:
    """
    Helper function to extract choices and their weights from a list of dictionaries.
    Each dictionary must have a 'weight' key.
    """
    choices = [choice for choice in weighted_choices]
    weights = [choice["weight"] for choice in weighted_choices]
    return choices, weights


def validate_resource_potential_definition(potential_data: Dict[str, Any], path: Path, resource_id: CommodityId):
    """Validates a single resource potential definition (range or bins)."""
    if "range" in potential_data:
        r_data = potential_data["range"]
        if not (isinstance(r_data, list) and len(r_data) == 2 and all(isinstance(x, (int, float)) for x in r_data) and r_data[0] <= r_data[1]):
            raise GenerationSchemaError(f"Invalid range for resource '{resource_id}' in {path}: {potential_data}")
    elif "bins" in potential_data:
        bins_data = potential_data["bins"]
        if not (isinstance(bins_data, list) and all(isinstance(b, dict) and "value" in b and "weight" in b and isinstance(b["value"], (int, float)) and isinstance(b["weight"], (int, float)) and b["weight"] >= 0 for b in bins_data)):
            raise GenerationSchemaError(f"Invalid bins for resource '{resource_id}' in {path}: {potential_data}")
    else:
        raise GenerationSchemaError(f"Resource potential for '{resource_id}' in {path} must define 'range' or 'bins': {potential_data}")


def validate_planet_type_schema(data: List[Dict[str, Any]], path: Path):
    """Validates the schema for planet_types.yaml."""
    if not isinstance(data, list):
        raise GenerationSchemaError(f"Top level of {path} must be a list of planet types.")

    for pt_data in data:
        for key in ["id", "name", "weight", "habitability_distribution", "resource_tables"]:
            if key not in pt_data:
                raise GenerationSchemaError(f"Missing key '{key}' in planet type '{pt_data.get('id', 'N/A')}' in {path}")
        
        if not isinstance(pt_data["id"], str) or not pt_data["id"]:
            raise GenerationSchemaError(f"Invalid or empty 'id' in planet type in {path}: {pt_data['id']}")
        if not isinstance(pt_data["name"], str) or not pt_data["name"]:
            raise GenerationSchemaError(f"Invalid or empty 'name' in planet type '{pt_data['id']}' in {path}: {pt_data['name']}")
        if not (isinstance(pt_data["weight"], (int, float)) and pt_data["weight"] > 0):
            raise GenerationSchemaError(f"Invalid 'weight' in planet type '{pt_data['id']}' in {path}: {pt_data['weight']}")

        # Validate habitability_distribution
        if not (isinstance(pt_data["habitability_distribution"], list) and len(pt_data["habitability_distribution"]) > 0):
            raise GenerationSchemaError(f"Invalid 'habitability_distribution' in planet type '{pt_data['id']}' in {path}")
        for h_dist in pt_data["habitability_distribution"]:
            if not ("band" in h_dist and "weight" in h_dist and isinstance(h_dist["band"], list) and len(h_dist["band"]) == 2 and all(isinstance(x, (int, float)) and 0.0 <= x <= 1.0 for x in h_dist["band"]) and h_dist["band"][0] <= h_dist["band"][1] and isinstance(h_dist["weight"], (int, float)) and h_dist["weight"] > 0):
                raise GenerationSchemaError(f"Invalid habitability band in planet type '{pt_data['id']}' in {path}: {h_dist}")

        # Validate resource_tables
        if not isinstance(pt_data["resource_tables"], dict):
            raise GenerationSchemaError(f"Invalid 'resource_tables' in planet type '{pt_data['id']}' in {path}")
        for table_name, table_data in pt_data["resource_tables"].items():
            if not ("potentials" in table_data and (("when_habitability_gte" in table_data) or ("when_habitability_lt" in table_data))):
                raise GenerationSchemaError(f"Resource table '{table_name}' in planet type '{pt_data['id']}' in {path} must define 'potentials' and 'when_habitability_gte' or 'when_habitability_lt'.")
            
            # Ensure only one of gte/lt is present
            if ("when_habitability_gte" in table_data) and ("when_habitability_lt" in table_data):
                raise GenerationSchemaError(f"Resource table '{table_name}' in planet type '{pt_data['id']}' in {path} must define EITHER 'when_habitability_gte' OR 'when_habitability_lt', not both.")

            if "when_habitability_gte" in table_data and not (isinstance(table_data["when_habitability_gte"], (int, float)) and 0.0 <= table_data["when_habitability_gte"] <= 1.0):
                raise GenerationSchemaError(f"Invalid 'when_habitability_gte' in resource table '{table_name}' in planet type '{pt_data['id']}' in {path}")
            if "when_habitability_lt" in table_data and not (isinstance(table_data["when_habitability_lt"], (int, float)) and 0.0 <= table_data["when_habitability_lt"] <= 1.0):
                raise GenerationSchemaError(f"Invalid 'when_habitability_lt' in resource table '{table_name}' in planet type '{pt_data['id']}' in {path}")

            if not isinstance(table_data["potentials"], dict):
                raise GenerationSchemaError(f"Invalid 'potentials' in resource table '{table_name}' in planet type '{pt_data['id']}' in {path}")
            for resource_id_str, potential_data in table_data["potentials"].items():
                validate_resource_potential_definition(potential_data, path, CommodityId(resource_id_str))


def validate_system_template_schema(data: List[Dict[str, Any]], path: Path):
    """Validates the schema for system_templates.yaml."""
    if not isinstance(data, list):
        raise GenerationSchemaError(f"Top level of {path} must be a list of system templates.")

    for st_data in data:
        for key in ["id", "name", "min_planets", "max_planets", "planet_type_weights"]:
            if key not in st_data:
                raise GenerationSchemaError(f"Missing key '{key}' in system template '{st_data.get('id', 'N/A')}' in {path}")

        if not isinstance(st_data["id"], str) or not st_data["id"]:
            raise GenerationSchemaError(f"Invalid or empty 'id' in system template in {path}: {st_data['id']}")
        if not isinstance(st_data["name"], str) or not st_data["name"]:
            raise GenerationSchemaError(f"Invalid or empty 'name' in system template '{st_data['id']}' in {path}: {st_data['name']}")
        if not (isinstance(st_data["min_planets"], int) and st_data["min_planets"] >= 0):
            raise GenerationSchemaError(f"Invalid 'min_planets' in system template '{st_data['id']}' in {path}: {st_data['min_planets']}")
        if not (isinstance(st_data["max_planets"], int) and st_data["max_planets"] >= st_data["min_planets"]):
            raise GenerationSchemaError(f"Invalid 'max_planets' in system template '{st_data['id']}' in {path}: {st_data['max_planets']}")
        if not (isinstance(st_data["planet_type_weights"], dict) and len(st_data["planet_type_weights"]) > 0):
            raise GenerationSchemaError(f"Invalid 'planet_type_weights' in system template '{st_data['id']}' in {path}")
        for pt_id, weight in st_data["planet_type_weights"].items():
            if not (isinstance(pt_id, str) and isinstance(weight, (int, float)) and weight >= 0):
                raise GenerationSchemaError(f"Invalid planet type weight for '{pt_id}' in system template '{st_data['id']}' in {path}: {weight}")


def load_planet_types(path: Path) -> Dict[str, Any]:
    """Loads and validates planet types from a YAML file."""
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    if "planet_types" not in data:
        raise GenerationSchemaError(f"Missing 'planet_types' key in {path}")
    validate_planet_type_schema(data["planet_types"], path)
    return {pt["id"]: pt for pt in data["planet_types"]}


def load_system_templates(path: Path) -> Dict[str, Any]:
    """Loads and validates system templates from a YAML file."""
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    if "system_templates" not in data:
        raise GenerationSchemaError(f"Missing 'system_templates' key in {path}")
    validate_system_template_schema(data["system_templates"], path)
    return {st["id"]: st for st in data["system_templates"]}


def load_habitability_tables(path: Path) -> Dict[str, Any]:
    """Loads and validates habitability tables from a YAML file. (Currently minimal)"""
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    # No specific validation needed for this minimal file for now
    return data
