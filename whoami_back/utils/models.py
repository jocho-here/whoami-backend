from copy import deepcopy
from typing import Dict, List


def remove_keys(original: Dict, target_keys: List[str]) -> Dict:
    """
    Return a new dictionary with the target keys removed
    """
    new_dict = deepcopy(original)

    for k in target_keys:
        new_dict.pop(k, None)

    return new_dict


def exclude_unset(given_dict: Dict) -> Dict:
    """
    Excluding unset (or None valued) entries in the given dictionary
    """
    keys = list(given_dict.keys())

    for key in keys:
        if given_dict[key] is None:
            given_dict.pop(key)

    return given_dict


def nullify_text_columns(given_dict: Dict, *, indicator: str = " ") -> Dict:
    """
    Assign null to the text columns in the given_dict with
    given_dict[key] = indicator
    """
    for key in given_dict:
        if given_dict[key] == indicator:
            given_dict[key] = None

    return given_dict
