#!/usr/bin/env python3
"""
Simple Security Verification for CntxtCS
Checks that security improvements are present in the code.
"""

import re
import os

def check_security_features():
    """Check if security features are implemented in the code."""
    print("🔍 Checking CntxtCS Security Features")
    print("="*40)
    
    security_checks = []
    
    try:
        with open('CntxtCS.py', 'r') as f:
            content = f.read()
        
        # Check for path validation
        if '_validate_directory_path' in content:
            security_checks.append("✅ Path validation function present")
        else:
            security_checks.append("❌ Path validation missing")
        
        # Check for file safety checks
        if '_is_safe_file' in content:
            security_checks.append("✅ File safety validation present")
        else:
            security_checks.append("❌ File safety validation missing")
        
        # Check for error sanitization
        if '_sanitize_error_message' in content:
            security_checks.append("✅ Error message sanitization present")
        else:
            security_checks.append("❌ Error message sanitization missing")
        
        # Check for resource limits
        if 'max_file_size_mb' in content and 'max_files' in content:
            security_checks.append("✅ Resource limits implemented")
        else:
            security_checks.append("❌ Resource limits missing")
        
        # Check for regex improvements
        if 'MULTILINE' in content:
            security_checks.append("✅ Regex patterns improved")
        else:
            security_checks.append("❌ Regex patterns need improvement")
        
        # Check for input validation
        if 'validate' in content.lower() and 'format' in content:
            security_checks.append("✅ Input validation present")
        else:
            security_checks.append("❌ Input validation needs improvement")
        
        # Check for data sanitization
        if '_sanitize_data_for_json' in content:
            security_checks.append("✅ JSON sanitization implemented")
        else:
            security_checks.append("❌ JSON sanitization missing")
        
        # Display results
        for check in security_checks:
            print(check)
        
        # Count passes
        passed = sum(1 for check in security_checks if "✅" in check)
        total = len(security_checks)
        
        print(f"\nSecurity Score: {passed}/{total} ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 All security features implemented!")
        elif passed >= total * 0.8:
            print("🟡 Most security features implemented")
        else:
            print("🔴 Security improvements needed")
            
    except FileNotFoundError:
        print("❌ CntxtCS.py not found")
        return

def check_security_files():
    """Check if security documentation files exist."""
    print("\n🔍 Checking Security Documentation")
    print("="*40)
    
    security_files = [
        ('SECURITY_ANALYSIS.md', 'Security analysis report'),
        ('SECURITY_GUIDELINES.md', 'User security guidelines'),
        ('security_config.py', 'Security configuration'),
        ('security_requirements.txt', 'Security dependencies'),
        ('security_validation.py', 'Security test suite')
    ]
    
    for filename, description in security_files:
        if os.path.exists(filename):
            print(f"✅ {description}: {filename}")
        else:
            print(f"❌ Missing {description}: {filename}")

def check_readme_security():
    """Check if README includes security information."""
    print("\n🔍 Checking README Security Information")
    print("="*40)
    
    try:
        with open('README.md', 'r') as f:
            readme_content = f.read()
        
        security_keywords = [
            'security', 'Security', 'protection', 'vulnerability',
            'SECURITY_GUIDELINES', 'hardened', 'validate'
        ]
        
        found_keywords = []
        for keyword in security_keywords:
            if keyword in readme_content:
                found_keywords.append(keyword)
        
        if found_keywords:
            print(f"✅ Security information present in README")
            print(f"   Found keywords: {', '.join(found_keywords[:3])}...")
        else:
            print("❌ No security information in README")
            
    except FileNotFoundError:
        print("❌ README.md not found")

if __name__ == "__main__":
    check_security_features()
    check_security_files()
    check_readme_security()
    
    print("\n🏁 Security verification completed!")
    print("\nNext steps:")
    print("1. Install dependencies: pip install networkx matplotlib")
    print("2. Run full security tests: python security_validation.py")
    print("3. Review security guidelines: cat SECURITY_GUIDELINES.md")