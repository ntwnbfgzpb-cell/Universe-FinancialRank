import argparse
import json

try:
    from .core.xbrl import normalize_xbrl_directory
except ImportError:
    from core.xbrl import normalize_xbrl_directory


def main():
    parser = argparse.ArgumentParser(description="MOPS XBRL 精確 tag 映射與單季化")
    parser.add_argument("directory")
    parser.add_argument("output_csv")
    parser.add_argument("--mapping")
    args = parser.parse_args()
    print(json.dumps(normalize_xbrl_directory(args.directory, args.output_csv, args.mapping),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
