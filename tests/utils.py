from typing import Union, Dict, List


def makeas(data: Union[Dict, List], expected: Union[Dict, List]) -> Union[List, Dict]:
    """
    Get fields the same as in expected. Works recursively
    """
    if isinstance(data, list):
        return [makeas(item, expected[0]) for item in data]

    if isinstance(data, dict):
        new_data = {}
        for key, value in data.items():
            if key not in expected:
                continue
            new_data[key] = makeas(value, expected[key])
        data = new_data

    return data
