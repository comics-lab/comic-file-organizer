#!/bin/bash

# DFA Project - Push to GitHub Script
# Run this after creating the GitHub repository

echo "=== DFA (Disk-Folder-File Analyzer) - GitHub Setup ==="
echo ""

# Prompt for repository name
read -p "Enter your GitHub repository name (e.g., disk-folder-file-analyzer): " repo_name

if [ -z "$repo_name" ]; then
    echo "Repository name cannot be empty!"
    exit 1
fi

echo ""
echo "Setting up GitHub remote for repository: $repo_name"
echo "GitHub URL will be: https://github.com/rmleonard/$repo_name"
echo ""

# Add remote
echo "Adding GitHub remote..."
git remote add origin "https://github.com/rmleonard/$repo_name.git"

# Push to GitHub
echo "Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS! Your DFA project is now on GitHub!"
    echo ""
    echo "🌐 Repository URL: https://github.com/rmleonard/$repo_name"
    echo "📁 Clone URL: https://github.com/rmleonard/$repo_name.git"
    echo ""
    echo "Your project includes:"
    echo "  ✅ Complete DFA application with all features"
    echo "  ✅ Comprehensive documentation (README.md)"
    echo "  ✅ Development log (DEVELOPMENT_LOG.md)"
    echo "  ✅ AI conversation transcript (AI_Build_for_dfa-main.md)"
    echo "  ✅ MIT License"
    echo "  ✅ Proper .gitignore"
    echo ""
    echo "🎉 Ready to share with the world!"
else
    echo ""
    echo "❌ Error pushing to GitHub. Please check:"
    echo "  1. Repository exists on GitHub"
    echo "  2. Repository name is correct"
    echo "  3. You have push permissions"
    echo "  4. Internet connection is working"
fi