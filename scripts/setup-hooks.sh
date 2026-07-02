#!/bin/bash

echo "🔧 Setting up git hooks..."

# Check if git-hooks directory exists
if [ ! -d "git-hooks" ]; then
    echo "❌ git-hooks directory not found!"
    exit 1
fi

# Copy all hooks to .git/hooks directory
cp -r git-hooks/* .git/hooks/
chmod +x .git/hooks/*

echo "✅ Git hooks installed successfully!"
