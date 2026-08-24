"""Role/permission seed placeholder; creates no patient rows."""
import argparse
p=argparse.ArgumentParser(description="Database seeder placeholder")
p.add_argument("--input-dir",required=True); p.add_argument("--output-dir",required=True)
if __name__=="__main__": p.parse_args(); raise SystemExit("NOT_IMPLEMENTED")
