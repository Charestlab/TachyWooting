"""
Header file processor for CFFI bindings.

This module is responsible for extracting relevant code from Wooting SDK header files
for use in generating CFFI bindings. It processes both the common and wrapper header
files, removing comments and unnecessary declarations while preserving the essential
C declarations needed for the Python interface.

The module filters out:
- Comments (starting with #, /, or *)
- Empty lines
- External declarations
- Other non-essential content
"""

def extract_header_code(common_header_path, wrapper_header_path):
    """
    Extract C code from header files for CFFI bindings.
    
    Args:
        common_header_path: Path to the common header file
        wrapper_header_path: Path to the wrapper header file
        
    Returns:
        Tuple containing extracted code from both header files
    """
    # Characters that indicate comments or preprocessor directives
    comment_chars = ['#', '/', '*']
    
    # Read header files
    with open(common_header_path, 'r') as file:
        common_header_content = file.readlines()
    with open(wrapper_header_path, 'r') as file:
        wrapper_header_content = file.readlines()

    # Process common header
    extracted_code_common = []
    for line in common_header_content:
        stripped_line = line.lstrip()
        if any(stripped_line) and stripped_line[0] not in comment_chars and 'extern' not in stripped_line:
            extracted_code_common.append(line)

    # Process wrapper header
    extracted_code_wrapper = []
    for line in wrapper_header_content:
        stripped_line = line.lstrip()
        if any(stripped_line) and stripped_line[0] not in comment_chars and 'extern' not in stripped_line:
            extracted_code_wrapper.append(line)

    return ''.join(extracted_code_common), ''.join(extracted_code_wrapper)

if __name__ == "__main__":
    # Test du module
    common_path = 'wootingSubLibrary/wooting-analog-common.h'
    wrapper_path = 'wootingSubLibrary/wooting-analog-wrapper.h'
    common_code, wrapper_code = extract_header_code(common_path, wrapper_path)
    print("Code extrait du fichier commun:")
    print(common_code)
    print("\nCode extrait du fichier wrapper:")
    print(wrapper_code)
