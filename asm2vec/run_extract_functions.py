import os
import click

IDA_PATH = os.getenv("IDA_PATH", "/opt/idapro-9.0/idat64")
LOG_PATH = "extract_log.txt"
IDA_PLUGIN = "extract_functions_ida.py"
@click.command()
@click.option('-i', '--binary', required=True,
              help='binary that we want to extract functions from.')
@click.option('-o', '--output-dir', required=True,
              help='Output directory.')
def main(binary, output_dir):
    cmd = [IDA_PATH,
            '-A',
            '-L{}'.format(LOG_PATH),
            '-S{}'.format(IDA_PLUGIN),
            '-Oextract_functions:{}'.format(
                output_dir),
            binary]
    print("Running command: {}".format(" ".join(cmd)))  

if __name__ == "__main__":
    main()