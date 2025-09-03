
def generate_filename(name: str) -> str:
    """
    Generate a filename based on the name.
    If the name already ends with 's', return as is.
    Otherwise, add 's' to the end.

    Args:
        name (str): The base name to convert

    Returns:
        str: The filename with proper pluralization
    """
    if name.endswith('s'):
        return name
    else:
        return name + 's'
