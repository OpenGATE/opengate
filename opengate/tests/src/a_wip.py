def is_function_defined_in_main(func_name):
    try:
        # Get the function object using its name
        func = globals()[func_name]

        # Get the filename where the function was defined
        filename = inspect.getsourcefile(func)

        # Read the source code of the file
        with open(filename, "r") as f:
            source_lines = f.readlines()

        # Find the line number where the function is defined
        func_line_number = None
        for i, line in enumerate(source_lines):
            if f"def {func_name}(" in line:
                func_line_number = i
                break

        if func_line_number is None:
            return False

        # Check if the function is defined after the main block
        for line in source_lines[func_line_number:]:
            if 'if __name__ == "__main__":' in line:
                return True
            elif "def " in line and func_line_number != i:
                # Encountered another function definition
                break

        return False
    except KeyError:
        # Function with the given name not found
        return False
