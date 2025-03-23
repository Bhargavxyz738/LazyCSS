import argparse
import os
import sys
from LazyCSS.build_manager import BuildManager

# SETTINGS
WATCH_FILE = "index.html"
OUTPUT_FILE = "style.css"
INCLUDE_CONFIG = False  

# CODES ARE SUBJECT TO LICENSE - Check LICENSE for more details
# THIS FILE "lazy.py" is made to manage Lazy CSS
# - Please provide a valid file name in WATCH_FILE.
# - Lazy CSS only supports one CSS file.  Multiple files will cause an error.
# - INCLUDE_CONFIG:
#     - Defaults to False.
#     - Set to True to use a 'lazy-config.json' file.
#     - Used for Lazy CSS configuration.
# - Lazy CSS is under development; more features are coming.
# - Requires 'watchdog'. Install with: pip install watchdog

""""
DO NOT CHANGE THE CODE BELOW
"""
def main():
    parser = argparse.ArgumentParser(description="Generate CSS from HTML with Lazy CSS.")
    parser.add_argument("input_file", nargs='?', help=f"Input HTML file (default: {WATCH_FILE})")
    parser.add_argument("output_file", nargs='?', help=f"Output CSS file (default: {OUTPUT_FILE})")
    parser.add_argument("-b", "--build", action="store_true", help="Perform a single build and exit")
    parser.add_argument("-c", "--config", action="store_const", const=True, default=INCLUDE_CONFIG,
                        help=f"Include and use lazy-config.json (default: {INCLUDE_CONFIG})")
    args = parser.parse_args()
    include_config = args.config
    build_manager = BuildManager(include_config=include_config)
    input_filepath = args.input_file or build_manager.config.get("input_file", WATCH_FILE)
    output_filepath = args.output_file or build_manager.config.get("output_file", OUTPUT_FILE)
    if not os.path.exists(input_filepath):
        print(f"Error: Input file '{input_filepath}' not found.", file=sys.stderr)
        exit(1)
    output_dir = os.path.dirname(output_filepath)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if args.build:
        build_manager.build(input_filepath, output_filepath)
    else:
        build_manager.watch(input_filepath, output_filepath)

# RUN LAZY CSS
if __name__ == "__main__":
    main() 
