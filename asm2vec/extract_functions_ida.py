import idc
import idaapi
import os
import json 
import idautils
    
def extract_functions(output_dir):
    print("Extracting functions...")
    idc.auto_wait()
    # func = idc.get_next_func(0)  # Get the first function after the start (address 0)

    output_dict = {}
    input_path = idaapi.get_input_file_path()
    idb_path = input_path + ".i64"
    output_dict[idb_path] = []
    for func_start in idautils.Functions():
        func_end = idc.get_func_attr(func_start, idc.FUNCATTR_END)
        func_size = func_end - func_start

        output_dict[idb_path].append(func_start)
        print(f"start = {func_start} size = {func_size}", end="    ")
        
        # Get the next function in the list
    print("Done.")
    # output_dir = os.path.join(os.path.dirname(input_path)+"_selection/")
    print(f"Output dir: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "selected_" + os.path.basename(input_path) + ".json")
    
    with open(output_path, "w") as f_out:
        print("Dumping functions to JSON...")
        json.dump(output_dict, f_out)

    idaapi.qexit(0)


if __name__ == "__main__":
    plugin_options = idaapi.get_plugin_options("extract_functions").split(":")
    output_dir = plugin_options[0]
    extract_functions(output_dir)
    idaapi.qexit(0)