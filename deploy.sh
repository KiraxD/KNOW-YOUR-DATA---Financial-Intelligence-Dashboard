#!/bin/bash

# KNOW YOUR DATA - Quick Deployment Script
# Deploy to Render (Free tier Python hosting)

echo "🚀 KNOW YOUR DATA Deployment"
echo "=============================="
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install Git first."
    exit 1
fi

echo "📝 Step 1: Initialize Git Repository"
git init
git add .
git commit -m "Initial commit - KNOW YOUR DATA"
git branch -M main

echo ""
echo "🔗 Step 2: Create GitHub Repository"
echo "   1. Go to https://github.com/new"
echo "   2. Create a repository (e.g., 'know-your-data')"
echo "   3. Copy the repository URL"
echo ""
read -p "Enter your GitHub repository URL: " github_url

git remote add origin "$github_url"
git push -u origin main

echo ""
echo "✅ Code pushed to GitHub!"
echo ""
echo "📡 Step 3: Deploy to Render"
echo "   1. Go to https://render.com"
echo "   2. Sign up with GitHub"
echo "   3. Click 'New +' → 'Web Service'"
echo "   4. Select your 'know-your-data' repository"
echo "   5. Use these settings:"
echo "      - Name: know-your-data-api"
echo "      - Runtime: Python 3"
echo "      - Build command: pip install -r erp-dashboard/requirements.txt"
echo "      - Start command: cd erp-dashboard && gunicorn app:app"
echo "   6. Click 'Create Web Service'"
echo ""
echo "🌐 Step 4: Deploy Frontend to Netlify"
echo "   1. Go to https://netlify.com"
echo "   2. Click 'Add new site' → 'Import an existing project'"
echo "   3. Select GitHub and authorize"
echo "   4. Choose 'know-your-data' repository"
echo "   5. Use these settings:"
echo "      - Build command: (leave empty)"
echo "      - Publish directory: erp-dashboard/templates"
echo "   6. Click 'Deploy site'"
echo ""
echo "🎉 Done! Your app will be live soon."
echo ""
echo "📌 Next Steps:"
echo "   1. Wait for Render deployment (3-5 minutes)"
echo "   2. Wait for Netlify deployment (1-2 minutes)"
echo "   3. Copy the Render API URL"
echo "   4. Update API endpoints in script.js with your Render URL"
echo "   5. Redeploy to Netlify"
