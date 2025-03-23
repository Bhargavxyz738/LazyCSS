import re
import json
import os
import sys
from bs4 import BeautifulSoup
from typing import Dict, List
def escape_class_name(cls):
    return re.sub(r"[/\\^$*+?.()|[\]{},]", r"\\\g<0>", cls)
def parse_style(s, config, prop_map, color_palette):
    s = s.replace("_", " ")
    rule = ""
    color_match = re.match(r"^(bg|c|border)-([a-z]+)-(\d+)$", s)
    if color_match:
        type_, color, shade = color_match.groups()
        hex_color = color_palette.get(color, {}).get(shade)
        if hex_color:
            return f"{prop_map[type_]}:{hex_color};"
        return ""
    border_match = re.match(r"^(border(?:-[trbl])?)-\[(.*?)\]$", s)
    if border_match:
        prefix = border_match.group(1)
        border_values = [v.strip() for v in border_match.group(2).split(',')]
        width = border_values[0] if len(border_values) > 0 else '1px'
        style = border_values[1] if len(border_values) > 1 else 'solid'
        color = border_values[2] if len(border_values) > 2 else 'currentColor'
        lazy_color_match = re.match(r"^([a-z]+)-(\d+)$", color)
        if lazy_color_match:
            color_name, shade = lazy_color_match.groups()
            hex_color = color_palette.get(color_name, {}).get(shade)
            if hex_color:
                color = hex_color
        border_property = 'border'
        if prefix == 'border-t':
            border_property = 'border-top'
        elif prefix == 'border-r':
            border_property = 'border-right'
        elif prefix == 'border-b':
            border_property = 'border-bottom'
        elif prefix == 'border-l':
            border_property = 'border-left'
        return f"{border_property}:{width} {style} {color};"
    match = re.match(r"^gridCols-(\d+)$", s)
    if match:
        cols = int(match.group(1))
        if not re.match(r'[^0-9]',match.group(1)) :
          return f"grid-template-columns: repeat({cols}, minmax(0, 1fr));"
    match = re.match(r"^zIndex-\[(.*?)\]$", s)
    if match:
        z_index_value = match.group(1)
        if not re.match(r'[^0-9]',z_index_value) or z_index_value=="auto" :
          return f"z-index: {z_index_value};"
    match = re.match(r"^(hw|mp)-\[(.*?)\]$", s)
    if match:
        type_, vals = match.groups()
        vals = [v.strip() for v in vals.split(',')]
        a, b = (vals[0], vals[1]) if len(vals) > 1 else (vals[0], vals[0])
        if type_ == 'hw':
            return f"height:{a};width:{b};"
        else:
            return f"margin:{a};padding:{b};"
    match = re.match(rf"^({'|'.join(prop_map.keys())})-\[(.*?)\]$", s)
    if match:
        prop, val = match.groups()
        definition = prop_map.get(prop)
        if definition:
            if isinstance(definition, dict):
                return f"{definition.get('p')}:{val}{';position:absolute' if definition.get('pos') else ''};"
            else:
                return f"{definition}:{val};"
        return ""
    match = re.match(r"^(\w+)-\{(.*?)\}$", s)
    if match:
        prop, config_key = match.groups()
        if config_key in config and prop in prop_map:
            definition = prop_map[prop]
            if isinstance(definition, dict):
                return f"{definition.get('p')}:{config[config_key]}{';position:absolute' if definition.get('pos') else ''};"
            else:
                return f"{definition}:{config[config_key]};"
        return ""
    return ""
def generate_rule(cls, processed, config, prop_map, color_palette):
    if cls in processed:
        return ""
    processed.add(cls)
    responsive_match = re.match(r"^(sm|md|lg|xl)-\((.*?)\)$", cls)
    if responsive_match:
        return ""
    pseudo_match = re.match(r"^(hover|active)-\((.*?)\)$", cls)
    if pseudo_match:
        pseudo_class = pseudo_match.group(1)
        inner_classes = [c.strip() for c in pseudo_match.group(2).split(',')]
        combined_rule = ""
        for inner_cls in inner_classes:
            inner_rule = parse_style(inner_cls, config, prop_map, color_palette)
            if inner_rule:
                combined_rule += f".{escape_class_name(cls)}:{pseudo_class}{{{inner_rule}}}"
        return combined_rule
    rule = parse_style(cls, config, prop_map, color_palette)
    return f".{escape_class_name(cls)}{{{rule}}}" if rule else ""
def process_classes(elements, processed, config, prop_map, color_palette, breakpoints, media_queries, unique_class_counter):
    new_rules = []
    for el in elements:
        for cls in el.get('class', '').split():
            if cls in processed:
                continue
            responsive_match = re.match(r"^(sm|md|lg|xl)-\((.*?)\)$", cls)
            if responsive_match:
                breakpoint = responsive_match.group(1)
                class_queries = [c.strip() for c in responsive_match.group(2).split(',')]
                for query in class_queries:
                    unique_class_name = f"lazy-responsive-{breakpoint}-{unique_class_counter[0]}"
                    unique_class_counter[0] += 1
                    current_classes = el.get('class','').split()
                    if unique_class_name not in current_classes:
                       el['class'] = f"{el.get('class','')} {unique_class_name}".strip()
                    rule = parse_style(query, config, prop_map, color_palette)
                    if rule:
                        media_rule = f".{escape_class_name(unique_class_name)} {{ {rule} }}"
                        if breakpoint not in media_queries:
                            media_queries[breakpoint] = []
                        media_queries[breakpoint].append(media_rule)
            else:
                rule = generate_rule(cls, processed, config, prop_map, color_palette)
                if rule:
                    new_rules.append(rule)
    return new_rules
def generate_css(html_string: str, config: Dict = None) -> str:
    if config is None:
        config = {}
    prop_map = {
        'bg': 'background-color', 'c': 'color', 'round': 'border-radius', 'ml': 'margin-left', 'm': 'margin',
        'mr': 'margin-right', 'h': 'height', 'w': 'width', 'mt': 'margin-top', 'mb': 'margin-bottom',
        'pl': 'padding-left', 'p': 'padding', 'pr': 'padding-right', 'pt': 'padding-top', 'pb': 'padding-bottom',
        'l': {'p': 'left', 'pos': 1}, 'r': {'p': 'right', 'pos': 1}, 't': {'p': 'top', 'pos': 1},
        'b': {'p': 'bottom', 'pos': 1}, 'fs': 'font-size', 'border': 'border-color', 'z': 'z-index',
        'gridCols': 'grid-template-columns', 'gap': 'gap'
    }
    color_palette = {
        'orange': {'50': '#fff7ed', '100': '#FFE8D1', '200': '#FFD1A4', '300': '#FFB877', '400': '#FF9F4A',
                   '500': '#FF8500', '600': '#E57700', '700': '#CC6900', '800': '#B35A00', '900': '#994B00',
                   '950': '#431407'},
        'black': {'50': '#e6e6e6', '100': '#cccccc', '200': '#999999', '300': '#666666', '400': '#333333',
                 '500': '#1a1a1a', '600': '#0d0d0d', '700': '#080808', '800': '#040404', '900': '#020202',
                 '950': '#000000'},
        'gray': {'50': '#f9fafb', '100': '#f3f4f6', '200': '#e5e7eb', '300': '#d1d5db', '400': '#9ca3af',
                '500': '#6b7280', '600': '#4b5563', '700': '#374151', '800': '#1f2937', '900': '#111827',
                '950': '#030712'},
        'red': {'50': '#fef2f2', '100': '#fee2e2', '200': '#fecaca', '300': '#fca5a5', '400': '#f87171',
                '500': '#ef4444', '600': '#dc2626', '700': '#b91c1c', '800': '#991b1b', '900': '#7f1d1d',
                '950': '#450a0a'},
        'yellow': {'50': '#fefce8', '100': '#fef9c3', '200': '#fef08a', '300': '#fde047', '400': '#facc15',
                  '500': '#eab308', '600': '#ca8a04', '700': '#a16207', '800': '#854d0e', '900': '#713f12',
                  '950': '#422006'},
        'green': {'50': '#f0fdf4', '100': '#dcfce7', '200': '#bbf7d0', '300': '#86efac', '400': '#4ade80',
                  '500': '#22c55e', '600': '#16a34a', '700': '#15803d', '800': '#166534', '900': '#14532d',
                  '950': '#052e16'},
        'blue': {'50': '#eff6ff', '100': '#dbeafe', '200': '#bfdbfe', '300': '#93c5fd', '400': '#60a5fa',
                 '500': '#3b82f6', '600': '#2563eb', '700': '#1d4ed8', '800': '#1e40af', '900': '#1e3a8a',
                 '950': '#172554'},
        'purple': {'50': '#faf5ff', '100': '#ede9fe', '200': '#ddd6fe', '300': '#c4b5fd', '400': '#a78bfa',
                  '500': '#8b5cf6', '600': '#7c3aed', '700': '#6d28d9', '800': '#5b21b6', '900': '#4c1d95',
                  '950': '#2e1065'},
        'pink': {'50': '#fdf2f8', '100': '#fce7f3', '200': '#fbcfe8', '300': '#f9a8d4', '400': '#f472b6',
                  '500': '#ec4899', '600': '#db2777', '700': '#be185d', '800': '#9d174d', '900': '#831843',
                  '950': '#500724'},
        'lime': {'50': '#f7fee7', '100': '#ecfccb', '200': '#d9f99d', '300': '#bef264', '400': '#a3e635',
                '500': '#84cc16', '600': '#65a30d', '700': '#4d7c0f', '800': '#3f6212', '900': '#365314',
                '950': '#1a2e05'},
        'teal': {'50': '#f0fdfa', '100': '#ccfbf1', '200': '#99f6e4', '300': '#5eead4', '400': '#2dd4bf',
                '500': '#14b8a6', '600': '#0d9488', '700': '#0f766e', '800': '#115e59', '900': '#134e4a',
                '950': '#042f2e'},
        'cyan': {'50': '#ecfeff', '100': '#cffafe', '200': '#a5f3fc', '300': '#67e8f9', '400': '#22d3ee',
                '500': '#06b6d4', '600': '#0891b2', '700': '#0e7490', '800': '#155e75', '900': '#164e63',
                '950': '#083344'},
        'sky': {'50': '#f0f9ff', '100': '#e0f2fe', '200': '#bae6fd', '300': '#7dd3fc', '400': '#38bdf8',
               '500': '#0ea5e9', '600': '#0284c7', '700': '#0369a1', '800': '#075985', '900': '#0c4a6e',
               '950': '#082f49'},
        'indigo': {'50': '#eef2ff', '100': '#e0e7ff', '200': '#c7d2fe', '300': '#a5b4fc', '400': '#818cf8',
                  '500': '#6366f1', '600': '#4f46e5', '700': '#4338ca', '800': '#3730a3', '900': '#312e81',
                  '950': '#1e1b4b'},
        'violet': {'50': '#f5f3ff', '100': '#ede9fe', '200': '#ddd6fe', '300': '#c4b5fd', '400': '#a78bfa',
                  '500': '#8b5cf6', '600': '#7c3aed', '700': '#6d28d9', '800': '#5b21b6', '900': '#4c1d95',
                  '950': '#2e1065'},
        'fuchsia': {'50': '#fdf4ff', '100': '#fae8ff', '200': '#f5d0fe', '300': '#f0abfc', '400': '#e879f9',
                   '500': '#d946ef', '600': '#c026d3', '700': '#a21caf', '800': '#86198f', '900': '#701a75',
                   '950': '#4a044e'},
        'rose': {'50': '#fff1f2', '100': '#ffe4e6', '200': '#fecdd3', '300': '#fda4af', '400': '#fb7185',
                '500': '#f43f5e', '600': '#e11d48', '700': '#be123c', '800': '#9f1239', '900': '#881337',
                '950': '#4c0519'},
        'neutral': {'50': '#fafafa', '100': '#f5f5f5', '200': '#e5e5e5', '300': '#d4d4d4', '400': '#a3a3a3',
                   '500': '#737373', '600': '#525252', '700': '#404040', '800': '#262626', '900': '#171717',
                   '950': '#0a0a0a'},
        'stone': {'50': '#fafaf9', '100': '#f5f5f4', '200': '#e7e5e4', '300': '#d6d3d1', '400': '#a8a29e',
                 '500': '#78716c', '600': '#57534e', '700': '#44403c', '800': '#292524', '900': '#1c1917',
                 '950': '#0c0a09'},
        'zinc': {'50': '#fafafa', '100': '#f4f4f5', '200': '#e4e4e7', '300': '#d4d4d8', '400': '#a1a1aa',
                '500': '#71717a', '600': '#52525b', '700': '#3f3f46', '800': '#27272a', '900': '#18181b',
                '950': '#09090b'},
        'slate': {'50': '#f8fafc', '100': '#f1f5f9', '200': '#e2e8f0', '300': '#cbd5e1', '400': '#94a3b8',
                 '500': '#64748b', '600': '#475569', '700': '#334155', '800': '#1e293b', '900': '#0f172a',
                 '950': '#020617'}
    }
    breakpoints = {
        'sm': '640px',
        'md': '768px',
        'lg': '1024px',
        'xl': '1280px'
    }
    base_styles = {}
    lazy_json_path = os.path.join(os.path.dirname(__file__), "..", "classes", "lazy.json")
    try:
        with open(lazy_json_path, 'r') as f:
            base_styles = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find Lazy.json at {lazy_json_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in Lazy.json: {e}", file=sys.stderr)
        sys.exit(1)

    media_queries = {}
    processed = set()
    unique_class_counter = [0]
    soup = BeautifulSoup(html_string, 'html.parser')  
    elements: List[Dict] = []
    for tag in soup.find_all():
        if tag.has_attr('class'):
            element = {"class": " ".join(tag['class'])} 
            elements.append(element)
    lazy_config_match = re.search(r'<script id="lazy-config">([\s\S]*?)</script>', html_string)
    if lazy_config_match:
        lazy_config_content = lazy_config_match.group(1).strip()
        for line in lazy_config_content.split('\n'):
            line = line.strip()
            if line:
                try:
                    config.update(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Error parsing inline JSON: {e}, in line: {line}", file=sys.stderr)
    initial_css_rules = process_classes(elements, processed, config, prop_map, color_palette, breakpoints, media_queries, unique_class_counter)
    used_classes = {cls for el in elements for cls in el.get('class', '').split()}
    base_css_rules = [f".{cls} {{{rule}}}" for cls, rule in base_styles.items() if cls in used_classes]
    css_rules = []
    for rule in base_css_rules:
        css_rules.append(rule.replace('{', ' {\n    ').replace(';', ';\n    ').replace('}', '\n}\n'))
    for rule in initial_css_rules:
        css_rules.append(rule.replace('{', ' {\n    ').replace(';', ';\n    ').replace('}', '\n}\n'))
    custom_classes = config.get("custom_classes", {})
    custom_css_rules = []
    for class_name, styles in custom_classes.items():
       custom_css_rules.append(f".{escape_class_name(class_name)} {{\n    {styles}\n}}")
    css_rules.extend(custom_css_rules)
    css_output = '\n'.join(css_rules)
    formatted_media_queries = []
    for breakpoint, rules in media_queries.items():
        formatted_rules = []
        for rule in rules:
            formatted_rule = rule.replace('{', ' {\n        ').replace(';', ';\n        ').replace('}', '\n    }')
            formatted_rules.append(formatted_rule)
        media_query = f"\n@media (min-width: {breakpoints[breakpoint]}) {{\n    "
        media_query += '\n    '.join(formatted_rules)
        media_query += "\n}\n"
        formatted_media_queries.append(media_query)
    css_output += '\n'.join(formatted_media_queries)
    return css_output
