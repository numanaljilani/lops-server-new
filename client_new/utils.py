def generate_sequential_number(model_class, prefix, field_name):
    """
    Generate a sequential number in the format LETS-PREFIX-1001.

    Args:
        model_class: The model class to query
        prefix: The prefix (e.g., "QN", "JN", "INV")
        field_name: The field name to query (e.g., "quotation_number")
    
    Returns:
        A string with the formatted number
    """
    # Create the prefix pattern
    prefix_pattern = f"LETS-{prefix}-"
    
    # Use filter and __startswith to find all matching numbers
    existing_numbers = model_class.objects.filter(
        **{f"{field_name}__startswith": prefix_pattern}
    ).values_list(field_name, flat=True)
    
    # Find the highest sequence number
    highest_seq = 1000  # Start from 1000 (so first will be 1001)
    
    for number in existing_numbers:
        try:
            # Extract digits after the prefix
            suffix = number.replace(prefix_pattern, "")
            # Try to convert to int, ignoring non-numeric characters
            digits_only = ''.join(c for c in suffix if c.isdigit())
            if digits_only:
                seq = int(digits_only)
                highest_seq = max(highest_seq, seq)
        except (ValueError, AttributeError):
            continue
    
    # Next sequence is highest + 1
    next_sequence = highest_seq + 1
    
    # Generate the full number
    return f"LETS-{prefix}-{next_sequence}"