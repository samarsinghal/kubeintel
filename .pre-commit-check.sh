#!/bin/bash

echo "🔍 Pre-commit security and cleanup check..."

# Check for sensitive information
echo "Checking for AWS account IDs..."
if grep -r -E "[0-9]{12}" --exclude-dir=.git --exclude="*.md" --exclude=".env.example" --exclude=".pre-commit-check.sh" . | grep -v "YOUR_ACCOUNT_ID"; then
    echo "❌ Found potential AWS account IDs"
    exit 1
fi

echo "Checking for access keys..."
if grep -r -E "AKIA[0-9A-Z]{16}" --exclude-dir=.git --exclude=".pre-commit-check.sh" . ; then
    echo "❌ Found potential AWS access keys"
    exit 1
fi

echo "Checking for hardcoded secrets..."
if grep -r -i -E "(aws_secret_access_key|aws_access_key_id).*=" --exclude-dir=.git --exclude=".env.example" --exclude="*.md" --exclude=".pre-commit-check.sh" . ; then
    echo "❌ Found hardcoded AWS credentials"
    exit 1
fi

echo "Checking for backup files..."
if find . -name "*.backup" -o -name "*.bak" -o -name "*~" -o -name "*.orig" -o -name "*copy*" -o -name "*old*" -o -name "*save*" | grep -v ".git" | grep -v ".gitignore"; then
    echo "❌ Found backup files that should be removed"
    exit 1
fi

echo "Checking for temporary files..."
if find . -name "*.tmp" -o -name "*.log" -o -name ".DS_Store" | grep -v ".git" | grep -v ".gitignore"; then
    echo "❌ Found temporary files that should be cleaned"
    exit 1
fi

echo "Checking for broken/test files..."
if find . -name "*broken*" -o -name "*test_temp*" | grep -v ".git" | grep -v "test_" | grep -v ".gitignore"; then
    echo "❌ Found broken or temporary test files"
    exit 1
fi

echo "✅ All security checks passed!"
echo "✅ Codebase is ready for GitHub!"
