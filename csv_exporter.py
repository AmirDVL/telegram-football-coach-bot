import csv
import io
from typing import List, Dict, Any

def generate_csv(data: List[Dict[str, Any]], headers: List[str]) -> io.BytesIO:
    """
    Generates a CSV file in memory from a list of dictionaries.

    Args:
        data: A list of dictionaries, where each dictionary represents a row.
        headers: A list of strings representing the CSV headers.

    Returns:
        An io.BytesIO object containing the CSV data with a UTF-8 BOM.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction='ignore', quoting=csv.QUOTE_ALL)

    # Write headers
    writer.writeheader()

    # Write data rows
    writer.writerows(data)

    csv_content = output.getvalue()

    # Add BOM for UTF-8 to ensure proper display in Excel
    csv_bytes = b'\xef\xbb\xbf' + csv_content.encode('utf-8')

    return io.BytesIO(csv_bytes)
