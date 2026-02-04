"""
Consistency checker and data quality scoring.
Run: python scripts/data_consistency_check.py
"""
from pathlib import Path

from cognitive.skills.study.data_quality_agent import data_quality_service


def main():
    result = data_quality_service.compute(write_files=True)
    out_path_json = Path("reports/data_quality_report.json")
    out_path_md = Path("reports/data_quality_report.md")
    print(f"Quality JSON: {out_path_json.resolve()}")
    print(f"Quality Markdown: {out_path_md.resolve()}")
    print(result.get("markdown", ""))


if __name__ == "__main__":
    main()
