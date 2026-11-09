import r2pipe
import json

def extract_functions(binary_path, output_path, idb_path):
    # Start Radare2 in headless mode
    r2 = r2pipe.open(binary_path)
    # r2.cmd('e bin.baseaddr=0x0')  # Set the base address to 0
    # base_address = r2.cmd('iB')
    # print("Base address set to:", base_address)
    r2.cmd("aaa")  # Perform full analysis

    # Get the list of functions
    functions = r2.cmdj("aflj")  # Get function list in JSON format

    if not functions:
        print("No functions found.")
        return

    functions = [func["offset"] for func in functions]
    dic = {}
    dic[idb_path] = functions
    # Save the functions to a JSON file
    with open(output_path, "w") as f:
        json.dump(dic, f)

    print(f"Extracted {len(functions)} functions.")
    print(f"Output saved to {output_path}")

    # Close the Radare2 session
    r2.quit()

# Use arguments to specify the input and output files using arg

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <binary_file> <output_file> <idb_path>")
        sys.exit(1)

    binary_file = sys.argv[1]
    output_file = sys.argv[2]
    idb_path = sys.argv[3]
    extract_functions(binary_file, output_file, idb_path)