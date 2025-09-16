# Security Guidelines for CntxtCS Users

## Overview

CntxtCS is a powerful tool for analyzing C# codebases and generating knowledge graphs. To ensure secure usage, please follow these security guidelines.

## Pre-Analysis Security Checklist

### ✅ Source Code Validation
- [ ] **Verify code source**: Only analyze codebases from trusted sources
- [ ] **Scan for malware**: Run antivirus/anti-malware scans on the codebase directory
- [ ] **Check file permissions**: Ensure you have appropriate read permissions
- [ ] **Review file types**: Verify the directory contains only expected C# project files

### ✅ Environment Setup
- [ ] **Isolated environment**: Run CntxtCS in a sandboxed or isolated environment when possible
- [ ] **User privileges**: Run with minimal required user privileges (avoid administrator/root)
- [ ] **Network isolation**: Consider running offline or in a network-isolated environment
- [ ] **Disk space**: Ensure sufficient disk space for processing and output

## Input Security

### Directory Path Security
```bash
# ✅ Good: Absolute paths to known directories
/home/user/projects/my-csharp-app
C:\Users\User\Source\MyProject

# ❌ Avoid: Relative paths with traversal attempts
../../../sensitive-directory
C:\Windows\System32
```

### File Size Considerations
- CntxtCS limits file processing to 10MB per file by default
- Large files are automatically skipped with warnings
- Maximum 10,000 files processed per session

## Processing Security

### Resource Limits
- **Memory**: Monitor memory usage during processing
- **CPU**: Processing automatically times out after 1 hour
- **Disk**: Output files are limited to prevent disk exhaustion

### File Type Validation
CntxtCS only processes these file types:
- `.cs` (C# source files)
- `.csproj` (Project files)
- `.sln` (Solution files) 
- `.json` (Configuration files)
- `.config` (Package configuration)

## Output Security

### JSON Output Review
Before sharing generated JSON files:
- [ ] **Review for sensitive data**: Check for accidentally included credentials, secrets, or personal information
- [ ] **Validate structure**: Ensure JSON structure is as expected
- [ ] **Check file size**: Verify output file size is reasonable

### Visualization Security
- [ ] **Local viewing only**: Keep visualizations local unless intentionally sharing
- [ ] **No embedded scripts**: Generated visualizations don't contain executable code
- [ ] **Browser security**: Use updated browsers when viewing HTML visualizations

## Deployment Security

### Production Environment
```bash
# Set restrictive file permissions
chmod 755 CntxtCS.py
chmod 644 *.json

# Run with limited user account
sudo -u limited-user python CntxtCS.py
```

### CI/CD Integration
If integrating into CI/CD pipelines:
- [ ] **Separate build stage**: Run analysis in isolated build containers
- [ ] **Artifact scanning**: Scan output artifacts for sensitive data
- [ ] **Access controls**: Limit access to generated knowledge graphs
- [ ] **Retention policies**: Implement data retention and cleanup policies

## Incident Response

### If Security Issues Are Detected
1. **Stop processing immediately**
2. **Isolate the environment**
3. **Document the issue**
4. **Report to security team**
5. **Review logs and outputs**

### Warning Signs
Watch for these indicators:
- Extremely long processing times
- Unexpected file access attempts
- Unusually large output files
- Memory or disk exhaustion
- Error messages indicating path traversal

## Security Updates

### Keeping CntxtCS Secure
- [ ] **Monitor for updates**: Check GitHub repository regularly
- [ ] **Review security advisories**: Subscribe to security notifications
- [ ] **Update dependencies**: Keep Python and required packages updated
- [ ] **Test in staging**: Test updates in non-production environments first

### Dependency Security
Regularly update these dependencies:
```bash
pip install --upgrade networkx matplotlib
pip audit  # Check for known vulnerabilities
```

## Data Privacy

### Sensitive Information Handling
- **Code comments**: Review for embedded passwords, API keys, or personal data
- **Hardcoded credentials**: Check for secrets in configuration files
- **Personal information**: Validate no PII is included in analysis
- **Proprietary information**: Ensure appropriate handling of proprietary code

### Sharing Generated Graphs
Before sharing knowledge graphs:
- [ ] **Data classification review**
- [ ] **Legal/compliance approval** 
- [ ] **Remove sensitive metadata**
- [ ] **Apply appropriate access controls**

## Compliance Considerations

### Regulatory Requirements
- **GDPR**: Ensure personal data protection compliance
- **HIPAA**: Special care for healthcare-related codebases
- **SOX**: Financial industry compliance requirements
- **Industry standards**: Follow sector-specific security standards

## Security Features Enabled

CntxtCS includes these built-in security features:

✅ **Path traversal protection**  
✅ **File size limits**  
✅ **Processing timeouts**  
✅ **Input validation**  
✅ **Error message sanitization**  
✅ **Resource exhaustion protection**  
✅ **Safe JSON serialization**  
✅ **Regex DoS prevention**  

## Need Help?

For security questions or to report vulnerabilities:
1. Create a GitHub issue (for general questions)
2. Contact maintainers directly (for security vulnerabilities)
3. Follow responsible disclosure practices

---

**Remember**: Security is a shared responsibility. Always err on the side of caution when analyzing unknown or untrusted codebases.