#!/usr/bin/env python3
"""
Merge all account JSON files from the accounts/ directory into a single list.
Can be run directly or imported as a module.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any


def merge_accounts(accounts_dir: str = "accounts", output_file: str = "accounts_merged.json") -> List[Dict[str, Any]]:
    """
    Merge all JSON files from accounts directory into a single list.
    
    Args:
        accounts_dir: Directory containing account JSON files
        output_file: Output file path for merged accounts
        
    Returns:
        List of all account dictionaries
    """
    accounts_path = Path(accounts_dir)
    
    if not accounts_path.exists():
        print(f"❌ Directory '{accounts_dir}' not found")
        return []
    
    all_accounts = []
    json_files = list(accounts_path.glob("*.json"))
    
    if not json_files:
        print(f"⚠️  No JSON files found in '{accounts_dir}'")
        return []
    
    print(f"📂 Found {len(json_files)} account file(s)")
    
    for json_file in sorted(json_files):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Handle both list and single object formats
                if isinstance(data, list):
                    all_accounts.extend(data)
                    print(f"  ✓ {json_file.name}: {len(data)} account(s)")
                elif isinstance(data, dict):
                    all_accounts.append(data)
                    print(f"  ✓ {json_file.name}: 1 account")
                else:
                    print(f"  ⚠️  {json_file.name}: Unexpected format, skipped")
                    
        except json.JSONDecodeError as e:
            print(f"  ❌ {json_file.name}: Invalid JSON - {e}")
        except Exception as e:
            print(f"  ❌ {json_file.name}: Error - {e}")
    
    # Write merged accounts to output file
    if all_accounts:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_accounts, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Merged {len(all_accounts)} account(s) → {output_file}")
    else:
        print("\n⚠️  No accounts to merge")
    
    return all_accounts


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Merge account JSON files into a single list")
    parser.add_argument(
        "--dir",
        default="accounts",
        help="Directory containing account JSON files (default: accounts)"
    )
    parser.add_argument(
        "--output",
        default="accounts_merged.json",
        help="Output file path (default: accounts_merged.json)"
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print merged accounts to stdout instead of file"
    )
    
    args = parser.parse_args()
    
    accounts = merge_accounts(args.dir, args.output)
    
    if args.print and accounts:
        print("\n" + "="*50)
        print(json.dumps(accounts, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
