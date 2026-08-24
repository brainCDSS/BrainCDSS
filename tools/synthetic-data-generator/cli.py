"""Metadata-only generator placeholder; creates no medical files."""
import argparse
p=argparse.ArgumentParser(description="Synthetic JSON metadata generator placeholder")
p.add_argument("--output-dir",required=True)
if __name__=="__main__": p.parse_args(); raise SystemExit("NOT_IMPLEMENTED")
