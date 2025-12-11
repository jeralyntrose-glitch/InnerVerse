#!/usr/bin/env python3
"""
Training Pair Contradiction Scanner
Scans all JSONL files for position/attitude mismatches
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple

# Red flag patterns: position + wrong attribute
CONTRADICTION_PATTERNS = [
    # Child position with inferior attributes
    (r'(child|3rd).*(fear|fears|insecurity|insecurities|pessimistic|worr)', 
     'Child position should be optimistic/innocent, not fears/insecurities'),
    
    # Inferior position with child attributes
    (r'(inferior|4th).*(innocent|innocence|optimistic|divine|playful)', 
     'Inferior position should be pessimistic/fears, not innocent/optimistic'),
    
    # Hero position with pessimistic attributes
    (r'(hero|1st|dominant).*(pessimistic|fear|fears|insecurity|worr)', 
     'Hero position should be optimistic, not pessimistic/fears'),
    
    # Parent position with optimistic attributes (when clearly wrong)
    (r'(parent|2nd).*(optimistic|innocent|divine|playful)', 
     'Parent position should be pessimistic/responsible, not optimistic/innocent'),
    
    # Specific phrases that are always wrong
    (r'child.*represents.*(fear|fears|insecurity)', 
     'Child never represents fears - that is the inferior'),
    
    (r'inferior.*represents.*(innocent|innocence|divine)', 
     'Inferior never represents innocence - that is the child'),
]

def scan_file(filepath: Path) -> List[Dict]:
    """Scan a single JSONL file for contradictions"""
    issues = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    pair = json.loads(line)
                    if 'messages' not in pair or len(pair['messages']) < 2:
                        continue
                    
                    # Check both question and answer
                    question = pair['messages'][0].get('content', '')
                    answer = pair['messages'][1].get('content', '')
                    text_to_scan = f"{question} {answer}".lower()
                    
                    # Check each pattern
                    for pattern, explanation in CONTRADICTION_PATTERNS:
                        matches = re.finditer(pattern, text_to_scan, re.IGNORECASE)
                        for match in matches:
                            # Get context around the match (50 chars before/after)
                            start = max(0, match.start() - 50)
                            end = min(len(text_to_scan), match.end() + 50)
                            context = text_to_scan[start:end]
                            
                            issues.append({
                                'file': filepath.name,
                                'line': line_num,
                                'pattern': pattern,
                                'match': match.group(0),
                                'context': context,
                                'explanation': explanation,
                                'question_preview': question[:100] if len(question) > 100 else question,
                                'answer_preview': answer[:200] if len(answer) > 200 else answer
                            })
                
                except json.JSONDecodeError as e:
                    issues.append({
                        'file': filepath.name,
                        'line': line_num,
                        'error': f'Invalid JSON: {e}'
                    })
    
    except Exception as e:
        issues.append({
            'file': filepath.name,
            'error': f'File read error: {e}'
        })
    
    return issues

def scan_all_files(base_path: Path) -> Dict[str, List[Dict]]:
    """Scan all JSONL files in pending_review and approved folders"""
    results = {
        'pending': [],
        'approved': [],
        'total_files': 0,
        'total_pairs_scanned': 0,
        'total_issues': 0
    }
    
    # Scan pending_review
    pending_dir = base_path / "pending_review"
    if pending_dir.exists():
        for jsonl_file in pending_dir.glob("*.jsonl"):
            results['total_files'] += 1
            issues = scan_file(jsonl_file)
            if issues:
                results['pending'].append({
                    'file': jsonl_file.name,
                    'path': str(jsonl_file),
                    'issues': issues
                })
                results['total_issues'] += len(issues)
            
            # Count pairs
            try:
                with open(jsonl_file, 'r') as f:
                    results['total_pairs_scanned'] += sum(1 for line in f if line.strip())
            except:
                pass
    
    # Scan approved
    approved_dir = base_path / "approved"
    if approved_dir.exists():
        for jsonl_file in approved_dir.glob("*.jsonl"):
            results['total_files'] += 1
            issues = scan_file(jsonl_file)
            if issues:
                results['approved'].append({
                    'file': jsonl_file.name,
                    'path': str(jsonl_file),
                    'issues': issues
                })
                results['total_issues'] += len(issues)
            
            # Count pairs
            try:
                with open(jsonl_file, 'r') as f:
                    results['total_pairs_scanned'] += sum(1 for line in f if line.strip())
            except:
                pass
    
    return results

def print_report(results: Dict):
    """Print a formatted report"""
    print("=" * 80)
    print("TRAINING PAIR CONTRADICTION SCAN REPORT")
    print("=" * 80)
    print(f"\nTotal files scanned: {results['total_files']}")
    print(f"Total pairs scanned: {results['total_pairs_scanned']}")
    print(f"Total issues found: {results['total_issues']}")
    print("=" * 80)
    
    if results['total_issues'] == 0:
        print("\n✅ NO CONTRADICTIONS FOUND!")
        return
    
    # Print pending issues
    if results['pending']:
        print("\n🚨 PENDING REVIEW FILES WITH ISSUES:")
        print("-" * 80)
        for file_data in results['pending']:
            print(f"\n📄 File: {file_data['file']}")
            print(f"   Path: {file_data['path']}")
            print(f"   Issues: {len(file_data['issues'])}")
            for issue in file_data['issues']:
                if 'error' in issue:
                    print(f"   ⚠️  Line {issue['line']}: {issue['error']}")
                else:
                    print(f"\n   🔴 Line {issue['line']}: CONTRADICTION DETECTED")
                    print(f"      Pattern: {issue['pattern']}")
                    print(f"      Match: '{issue['match']}'")
                    print(f"      Issue: {issue['explanation']}")
                    print(f"      Context: ...{issue['context']}...")
                    print(f"      Question: {issue['question_preview']}")
                    print(f"      Answer: {issue['answer_preview']}")
    
    # Print approved issues
    if results['approved']:
        print("\n🚨 APPROVED FILES WITH ISSUES:")
        print("-" * 80)
        for file_data in results['approved']:
            print(f"\n📄 File: {file_data['file']}")
            print(f"   Path: {file_data['path']}")
            print(f"   Issues: {len(file_data['issues'])}")
            for issue in file_data['issues']:
                if 'error' in issue:
                    print(f"   ⚠️  Line {issue['line']}: {issue['error']}")
                else:
                    print(f"\n   🔴 Line {issue['line']}: CONTRADICTION DETECTED")
                    print(f"      Pattern: {issue['pattern']}")
                    print(f"      Match: '{issue['match']}'")
                    print(f"      Issue: {issue['explanation']}")
                    print(f"      Context: ...{issue['context']}...")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATION:")
    print("Review each flagged pair and either:")
    print("  1. Delete the pair if it's clearly wrong")
    print("  2. Edit the pair to fix the contradiction")
    print("=" * 80)

def scan_pairs_list(pairs: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Scan a list of Q&A pairs and return (filtered_pairs, rejected_pairs)
    Used for automatic filtering during generation.
    """
    filtered_pairs = []
    rejected_pairs = []
    
    for pair in pairs:
        if 'messages' not in pair or len(pair['messages']) < 2:
            continue
        
        question = pair['messages'][0].get('content', '')
        answer = pair['messages'][1].get('content', '')
        text_to_scan = f"{question} {answer}".lower()
        
        # Check for contradictions
        has_contradiction = False
        for pattern, explanation in CONTRADICTION_PATTERNS:
            if re.search(pattern, text_to_scan, re.IGNORECASE):
                has_contradiction = True
                rejected_pairs.append({
                    'pair': pair,
                    'reason': explanation,
                    'match': re.search(pattern, text_to_scan, re.IGNORECASE).group(0)
                })
                break
        
        if not has_contradiction:
            filtered_pairs.append(pair)
    
    return filtered_pairs, rejected_pairs

def main():
    # Determine base path (works in both dev and production)
    base_path = Path("./data/training_pairs")
    
    if not base_path.exists():
        print(f"❌ Training pairs directory not found: {base_path}")
        print("   Make sure you're running from the project root")
        return
    
    print(f"Scanning: {base_path}")
    results = scan_all_files(base_path)
    print_report(results)
    
    # Save report to file
    report_path = base_path / "contradiction_report.json"
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n📊 Full report saved to: {report_path}")

if __name__ == "__main__":
    main()

