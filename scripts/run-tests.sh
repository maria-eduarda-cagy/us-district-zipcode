#!/bin/bash

echo "🔍 Running tests before commit..."

# Check if deno is installed
if ! command -v deno &> /dev/null
then
    echo "❌ Deno is not installed! Please install Deno to run the tests."
    exit 1
fi

# Run Deno tests for Supabase Edge Functions
echo "🧪 Running Supabase Edge Functions tests..."
deno test -A supabase/functions/search supabase/functions/sample-ballot

if [ $? -eq 0 ]; then
    echo "✅ All tests passed! Proceeding with commit."
    exit 0
else
    echo "❌ Tests failed! Please fix the issues before committing."
    exit 1
fi
