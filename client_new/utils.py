# client_new/utils.py
import datetime
from decimal import Decimal

def generate_sequential_number(model_class, prefix, field_name):
    """
    Generate a sequential number in the format PREFIX-YYMM1001
    
    Args:
        model_class: The model class to query
        prefix: The prefix (e.g., "QN", "JN", "INV")
        field_name: The field name to query (e.g., "quotation_number")
    
    Returns:
        A string with the formatted number
    """
    today = datetime.date.today()
    year_month = today.strftime("%y%m")
    
    # Find the latest number for this year-month
    prefix_pattern = f"LETS-{prefix}-{year_month}"
    
    # Use filter and __startswith to find all matching numbers
    existing_numbers = model_class.objects.filter(
        **{f"{field_name}__startswith": prefix_pattern}
    ).values_list(field_name, flat=True)
    
    # Extract the sequence numbers
    sequence_numbers = []
    for number in existing_numbers:
        # Try to extract the sequence part after the year-month
        try:
            seq = int(number.split(year_month)[1])
            sequence_numbers.append(seq)
        except (IndexError, ValueError):
            continue
    
    # Determine the next sequence number
    if sequence_numbers:
        next_sequence = max(sequence_numbers) + 1
    else:
        next_sequence = 1001  # Start from 1001
    
    # Generate the full number
    return f"LETS-{prefix}-{year_month}{next_sequence}"