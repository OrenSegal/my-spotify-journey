import logging

# Configure logging
logger = logging.getLogger('utils')

def sanitize_sql_query(query: str) -> str:
    """
    Fix common SQL syntax issues like multiple WHERE clauses.
    
    Args:
        query: SQL query string that might have syntax issues
    
    Returns:
        Corrected SQL query
    """
    # Split query into lines for easier processing
    lines = query.split('\n')
    result_lines = []
    prev_had_where = False
    
    for line in lines:
        # Check for the presence of WHERE keyword
        stripped_line = line.strip().upper()
        if stripped_line.startswith('WHERE '):
            if prev_had_where:
                # Replace WHERE with AND if we already have a WHERE clause
                line = line.replace('WHERE ', 'AND ', 1)
                line = line.replace('where ', 'AND ', 1)
            prev_had_where = True
        else:
            # Check if WHERE appears after other content in the line
            where_pos = stripped_line.find(' WHERE ')
            if where_pos > 0 and prev_had_where:
                # Replace WHERE with AND if it's not at the start and we already have a WHERE
                line = line.replace(' WHERE ', ' AND ', 1)
                line = line.replace(' where ', ' AND ', 1)
            elif where_pos > 0:
                prev_had_where = True
        
        result_lines.append(line)
    
    return '\n'.join(result_lines)