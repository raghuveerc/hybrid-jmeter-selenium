
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate multiple variations of an XML by replacing selected tags
(e.g., name, address, date, time) with unique values and different formats.
Outputs: a set of XML files and a CSV manifest.

Usage (basic):
    python generate_xml_variants.py \
        --input template.xml \
        --out out \
        --n 20 \
        --map name=.//Name,address=.//Address,date=.//Date,time=.//Time \
        --csv out/manifest.csv \
        --vary-formats \
        --seed 42 \
        --locale au

Notes:
- The --map option lets you map logical keys (name,address,date,time, or any custom keys)
  to element selectors. If the value starts with '.' or '/', it's treated as an XPath-like
  selector (limited ElementTree support). Otherwise, it is treated as a tag name and matched
  namespace-agnostically across the tree.
- If you skip --map, the script will try to find tags named: name, address, date, time (case-insensitive).
- By default, different formats for date/time are randomly picked per variant when --vary-formats
  is used. You can also specify explicit formats via --date-formats / --time-formats.
"""

import argparse
import csv
import os
import random
import string
import sys
import uuid
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional

# ---------------------------
# Helpers: XML utilities
# ---------------------------

def read_xml(path: str) -> ET.ElementTree:
    try:
        tree = ET.parse(path)
        return tree
    except ET.ParseError as e:
        sys.exit(f"[ERROR] Failed to parse XML '{path}': {e}")

def strip_ns(tag: str) -> str:
    """Strip namespace from a tag like '{ns}Local' -> 'Local'."""
    if '}' in tag:
        return tag.split('}', 1)[1]
    return tag

def find_elements_ns_agnostic(root: ET.Element, tag_name: str) -> List[ET.Element]:
    """Find all elements whose local-name equals tag_name (case-insensitive)."""
    t = tag_name.lower()
    return [el for el in root.iter() if strip_ns(el.tag).lower() == t]

def select_elements(root: ET.Element, selector: str) -> List[ET.Element]:
    """
    If selector looks like an XPath (starts with '.' or '/'), try root.findall(selector).
    Otherwise, treat it as a tag and do namespace-agnostic matching across the tree.
    """
    selector = selector.strip()
    if selector.startswith('.') or selector.startswith('/'):
        try:
            # Note: ElementTree's XPath is limited; no local-name() predicate support.
            els = root.findall(selector)
            return els
        except Exception:
            # Fallback to tag search by local-name if XPath fails
            return find_elements_ns_agnostic(root, selector.strip('./'))
    else:
        return find_elements_ns_agnostic(root, selector)

# ---------------------------
# Helpers: Random generators
# ---------------------------

AU_STATES = ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"]
AU_CITIES = [
    "Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide",
    "Canberra", "Hobart", "Newcastle", "Wollongong", "Geelong"
]
AU_STREETS = [
    "George St", "Pitt St", "Elizabeth St", "King St",
    "Market St", "Oxford St", "Queen St", "Collins St", "Bourke St", "Bridge St"
]

GENERIC_STATES = ["CA", "NY", "TX", "WA", "MA", "FL", "IL", "PA", "OH", "MI"]
GENERIC_CITIES = [
    "Springfield", "Fairview", "Riverton", "Greenville", "Madison",
    "Georgetown", "Franklin", "Arlington", "Clinton", "Dayton"
]
GENERIC_STREETS = [
    "Main St", "High St", "Park Ave", "Oak St", "Maple Ave",
    "Cedar St", "Pine St", "Elm St", "Washington Ave", "Lakeview Dr"
]

FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Sam", "Jamie",
    "Dee", "Kris", "Avery", "Cameron", "Hayden", "Rowan", "Sydney"
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis",
    "Wilson", "Anderson", "Thomas", "Jackson", "White", "Harris"
]

def random_name() -> Dict[str, str]:
    """Return a dict with multiple name formats; caller can pick one."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    middle = random.choice(string.ascii_uppercase)
    formats = {
        "first_last": f"{first} {last}",
        "last_first": f"{last}, {first}",
        "first_m_last": f"{first} {middle}. {last}",
        "u_case": f"{first.upper()} {last.upper()}",
        "l_case": f"{first.lower()} {last.lower()}",
    }
    return formats

def random_postcode(locale: str) -> str:
    if locale == "au":
        return f"{random.randint(2000, 7999)}"  # Common AU postcode range (not exhaustive)
    else:
        return f"{random.randint(10000, 99999)}"

def random_address(locale: str) -> Dict[str, str]:
    if locale == "au":
        streets = AU_STREETS
        cities = AU_CITIES
        states = AU_STATES
    else:
        streets = GENERIC_STREETS
        cities = GENERIC_CITIES
        states = GENERIC_STATES

    num = random.randint(1, 9999)
    street = random.choice(streets)
    city = random.choice(cities)
    state = random.choice(states)
    pc = random_postcode(locale)

    # Provide several address formats
    formats = {
        "one_line": f"{num} {street}, {city} {state} {pc}",
        "multi_line": f"{num} {street}\n{city} {state} {pc}",
        "with_country": f"{num} {street}, {city} {state} {pc}, Australia" if locale == "au"
                        else f"{num} {street}, {city} {state} {pc}, USA",
        "no_state": f"{num} {street}, {city} {pc}",
    }
    return formats

def random_date_between(start: datetime, end: datetime) -> datetime:
    delta = end - start
    seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=seconds)

DEFAULT_DATE_FORMATS = [
    "%Y-%m-%d",        # 2025-09-10
    "%d/%m/%Y",        # 10/09/2025
    "%m-%d-%Y",        # 09-10-2025
    "%d %b %Y",        # 10 Sep 2025
    "%B %d, %Y",       # September 10, 2025
    "%Y%m%d",          # 20250910
]

DEFAULT_TIME_FORMATS = [
    "%H:%M",           # 14:05
    "%H:%M:%S",        # 14:05:33
    "%I:%M %p",        # 02:05 PM
    "%H:%M:%S.%f",     # 14:05:33.123456
]

def random_tz_offset_str() -> str:
    # offsets from -12:00 to +14:00
    offset_hours = random.randint(-12, 14)
    offset_minutes = random.choice([0, 15, 30, 45])
    sign = "+" if offset_hours > 0 or (offset_hours == 0 and offset_minutes >= 0) else "-"
    return f"{sign}{abs(offset_hours):02d}:{abs(offset_minutes):02d}"

def format_date_time(dt: datetime, date_fmt: str, time_fmt: str, with_zone: bool = False) -> Tuple[str, str]:
    date_str = dt.strftime(date_fmt)
    if with_zone:
        # Append 'Z' (UTC) or numeric offset
        choice = random.choice(["Z", "offset"])
        if choice == "Z":
            time_str = (dt.replace(tzinfo=timezone.utc)).strftime(time_fmt) + "Z"
        else:
            off = random_tz_offset_str()
            time_str = dt.strftime(time_fmt) + off
    else:
        time_str = dt.strftime(time_fmt)
    return date_str, time_str

# ---------------------------
# Core generation
# ---------------------------

def parse_map_arg(map_arg: Optional[str]) -> Dict[str, str]:
    """
    Parse mapping like "name=.//Name,address=.//Address,date=.//Date,time=.//Time"
    into dict { 'name': './/Name', ... }
    """
    mapping = {}
    if not map_arg:
        return mapping
    for pair in map_arg.split(","):
        if not pair.strip():
            continue
        if "=" not in pair:
            sys.exit(f"[ERROR] --map entry '{pair}' must be key=selector")
        k, v = pair.split("=", 1)
        mapping[k.strip()] = v.strip()
    return mapping

def generate_variant_values(locale: str,
                            date_formats: List[str],
                            time_formats: List[str],
                            vary_formats: bool) -> Dict[str, str]:
    """
    Generate a single set of values for name/address/date/time, with formats chosen.
    Returns a dict that may include keys: name, address, date, time
    """
    values = {}

    # Name formats
    name_formats = random_name()
    name_choice = random.choice(list(name_formats.values()))
    values["name"] = name_choice

    # Address formats
    addr_formats = random_address(locale)
    addr_choice = random.choice(list(addr_formats.values()))
    values["address"] = addr_choice

    # Date/time formats
    start = datetime(2015, 1, 1)
    end = datetime.now()
    dt = random_date_between(start, end)

    if vary_formats:
        date_fmt = random.choice(date_formats)
        time_fmt = random.choice(time_formats)
        with_zone = random.choice([True, False])
    else:
        date_fmt = date_formats[0]
        time_fmt = time_formats[0]
        with_zone = False

    date_str, time_str = format_date_time(dt, date_fmt, time_fmt, with_zone=with_zone)
    values["date"] = date_str
    values["time"] = time_str

    return values

def apply_values_to_tree(tree: ET.ElementTree,
                         mapping: Dict[str, str],
                         values: Dict[str, str]) -> Tuple[ET.ElementTree, Dict[str, List[str]]]:
    """
    For each logical key in `mapping`, find elements and set their .text to generated value.
    Returns (new_tree, affected_paths) where affected_paths logs which selectors were hit.
    """
    # Clone tree by serialize/parse to avoid mutating original
    xml_bytes = ET.tostring(tree.getroot(), encoding="utf-8")
    new_root = ET.fromstring(xml_bytes)
    affected = {}

    for key, selector in mapping.items():
        val = values.get(key)
        if val is None:
            continue
        els = select_elements(new_root, selector)
        for el in els:
            el.text = val
        affected[key] = [selector] * len(els)

    return ET.ElementTree(new_root), affected

def ensure_unique(across: set, vals_tuple: Tuple[str, ...], max_attempts: int = 50) -> bool:
    """
    Ensure a tuple is unique by checking against a set; returns True if added, else False.
    """
    if vals_tuple in across:
        return False
    across.add(vals_tuple)
    return True

def main():
    parser = argparse.ArgumentParser(description="Generate multiple XML variants with randomized tag values.")
    parser.add_argument("--input", "-i", required=True, help="Path to template XML.")
    parser.add_argument("--out", "-o", required=True, help="Output directory for XMLs and/or CSV.")
    parser.add_argument("--n", type=int, default=10, help="Number of variants to generate (default: 10).")
    parser.add_argument("--csv", default=None, help="Path to manifest CSV (default: <out>/manifest.csv).")
    parser.add_argument("--map", default=None,
                        help="Mapping like 'name=.//Name,address=.//Address,date=.//Date,time=.//Time'. "
                             "If omitted, will try tag names name,address,date,time (namespace-agnostic).")
    parser.add_argument("--date-formats", default=",".join(DEFAULT_DATE_FORMATS),
                        help=f"Comma-separated date formats. Default: {', '.join(DEFAULT_DATE_FORMATS)}")
    parser.add_argument("--time-formats", default=",".join(DEFAULT_TIME_FORMATS),
                        help=f"Comma-separated time formats. Default: {', '.join(DEFAULT_TIME_FORMATS)}")
    parser.add_argument("--vary-formats", action="store_true", help="Randomly pick different formats per variant.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility.")
    parser.add_argument("--locale", choices=["generic", "au"], default="generic",
                        help="Basic address locale style (default: generic).")

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    # Prepare output dir
    os.makedirs(args.out, exist_ok=True)

    manifest_path = args.csv or os.path.join(args.out, "manifest.csv")

    # Load template
    template_tree = read_xml(args.input)
    template_root = template_tree.getroot()

    # Build mapping
    mapping = parse_map_arg(args.map)
    if not mapping:
        # Fallback: attempt default logical keys via tag-name matching
        mapping = {
            "name": "name",
            "address": "address",
            "date": "date",
            "time": "time",
        }

    date_formats = [fmt.strip() for fmt in args.date_formats.split(",") if fmt.strip()]
    time_formats = [fmt.strip() for fmt in args.time_formats.split(",") if fmt.strip()]

    # Output CSV
    fieldnames = ["variant_id", "xml_filename", "name", "address", "date", "time", "xml_content"]
    with open(manifest_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Track uniqueness across variants using the tuple of (name,address,date,time) that exist in mapping
        seen = set()

        base_name = os.path.splitext(os.path.basename(args.input))[0]

        count_generated = 0
        attempts = 0
        max_total_attempts = args.n * 20

        while count_generated < args.n and attempts < max_total_attempts:
            attempts += 1

            values = generate_variant_values(
                locale=args.locale,
                date_formats=date_formats,
                time_formats=time_formats,
                vary_formats=args.vary_formats
            )

            # Only include keys that are in mapping; this way the uniqueness pertains to used tags
            used_keys = [k for k in ["name", "address", "date", "time"] if k in mapping]
            vals_tuple = tuple(values.get(k, "") for k in used_keys)

            if not ensure_unique(seen, vals_tuple):
                continue  # duplicate, try again

            # Apply to tree
            new_tree, _affected = apply_values_to_tree(template_tree, mapping, values)

            # Serialize
            xml_bytes = ET.tostring(new_tree.getroot(), encoding="utf-8", xml_declaration=True)
            xml_text = xml_bytes.decode("utf-8")

            variant_id = count_generated + 1
            xml_filename = f"{base_name}_variant_{variant_id:03d}.xml"
            xml_path = os.path.join(args.out, xml_filename)

            with open(xml_path, "w", encoding="utf-8", newline="") as f:
                f.write(xml_text)

            # Write CSV row
            row = {
                "variant_id": variant_id,
                "xml_filename": xml_filename,
                "name": values.get("name", ""),
                "address": values.get("address", ""),
                "date": values.get("date", ""),
                "time": values.get("time", ""),
                "xml_content": xml_text
            }
            writer.writerow(row)

            count_generated += 1

    print(f"[OK] Generated {count_generated} variants in '{args.out}'.")
    print(f"[OK] Manifest written to '{manifest_path}'.")
    if attempts >= max_total_attempts and count_generated < args.n:
        print("[WARN] Stopped early due to uniqueness constraints. Consider increasing variability or reducing --n.")

if __name__ == "__main__":
    main()
