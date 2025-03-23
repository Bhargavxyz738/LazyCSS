import os
import sys
import time
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
try:
    from LazyCSS.Build.builder import generate_css
    from LazyCSS.Build.dump import write_css
except ImportError:
    print("Error: Could not import LazyCSS.  Ensure it's installed or in a sibling directory.", file=sys.stderr)
    sys.exit(1)

CONFIG_FILE = "lazy-config.json" 

class BuildManagerEventHandler(FileSystemEventHandler):
    def __init__(self, watch_filepath, css_filepath, build_manager):
        super().__init__()
        self.watch_file = watch_filepath
        self.css_file = css_filepath
        self.last_modified = 0
        self.last_css_content = self.get_current_css()
        self.build_manager = build_manager  
    def get_current_css(self):
        try:
            with open(self.css_file, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return ""
    def on_modified(self, event):
        if event.src_path == os.path.abspath(self.watch_file):
            current_modified = os.path.getmtime(self.watch_file)
            if current_modified > self.last_modified:
                self.last_modified = current_modified
                self.build_manager.build_and_compare(self.watch_file, self.css_file)
class BuildManager:
    def __init__(self, include_config=False):
        self.include_config = include_config
        self.config = {}
        self.load_config()  
        self.event_handler = None 
    def load_config(self):  
        if self.include_config:
            if not os.path.exists(CONFIG_FILE):
                self.create_default_config()
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
            except FileNotFoundError:
                 print(f"Warning: Could not find config {CONFIG_FILE}.", file=sys.stderr)
            except json.JSONDecodeError as e:
                print(f"Error loading config: {e}", file=sys.stderr)
    def create_default_config(self):
        default_config = {
            "input_file": "index.html",
            "output_file": "style.css",
            "custom_classes": {
                "my-button": """
                    background-color: blue;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 5px;
                """,
                "my-container": """
                    max-width: 960px;
                    margin: 0 auto;
                    padding: 20px;
                """
            }
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=4) 
            print(f"Created default config file: {CONFIG_FILE}")
        except Exception as e:
            print(f"Error creating config file: {e}", file=sys.stderr)
            sys.exit(1)
    def build(self, input_file, output_file):
        try:
            with open(input_file, 'r') as f:
                html_content = f.read()
            css = generate_css(html_content,self.config)
            write_css(output_file, css)
            if self.event_handler:
               self.event_handler.last_css_content = css
            print(f"Initialized {output_file}")
        except FileNotFoundError:
            print(f"Error: Could not find {input_file}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error during build: {e}", file=sys.stderr)
            sys.exit(1)
    def build_and_compare(self, input_file, output_file):
        try:
            with open(input_file, 'r') as f:
                html_content = f.read()
            new_css = generate_css(html_content,self.config) 
            if self.event_handler and new_css != self.event_handler.last_css_content: # Compare
                print("Detected change. Building...")
                start_time = time.time()
                write_css(output_file, new_css)
                self.event_handler.last_css_content = new_css 
                end_time = time.time()
                print(f"Build in {end_time - start_time:.3f} seconds")
        except Exception as e:
            print(f"Error during build: {e}", file=sys.stderr)
    def watch(self, input_file, output_file):
        self.event_handler = BuildManagerEventHandler(input_file, output_file, self) # Pass self
        self.build(input_file, output_file) 
        observer = Observer()
        observer.schedule(self.event_handler, path=os.path.dirname(os.path.abspath(input_file)) or '.', recursive=False)
        observer.start()
        print(f"Watching {input_file} for changes...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
