# Netlify Deployment Guide for KNOW YOUR DATA

## Option 1: Frontend Only (Recommended for Netlify)

Netlify works best with static sites. Since your app has a Flask backend, here's the best approach:

### Step 1: Deploy Frontend to Netlify

1. Push your code to GitHub:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/know-your-data.git
git push -u origin main
```

2. Connect to Netlify:
   - Go to https://netlify.com
   - Click "Add new site" → "Import an existing project"
   - Select GitHub and authorize
   - Choose your repository
   - Build settings:
     - Build command: (leave empty)
     - Publish directory: `erp-dashboard/templates`

3. Update frontend to connect to backend API

### Step 2: Deploy Backend to Render (Free)

1. Go to https://render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - Name: `know-your-data-api`
   - Runtime: `Python 3`
   - Build command: `pip install -r erp-dashboard/requirements.txt`
   - Start command: `cd erp-dashboard && gunicorn app:app`
   - Environment variables:
     - Add `FLASK_ENV = production`

5. Deploy!

6. Get your backend URL from Render (e.g., `https://know-your-data-api.onrender.com`)

### Step 3: Update Frontend API Calls

In `erp-dashboard/static/script.js`, update API endpoints:

Replace:

```javascript
fetch("/dashboard-data?session_id=" + sid);
```

With:

```javascript
fetch(
  "https://know-your-data-api.onrender.com/dashboard-data?session_id=" + sid,
);
```

---

## Option 2: Full Stack on Render (Simpler)

If you want to keep everything together, deploy the entire Flask app to Render:

1. Go to https://render.com → New Web Service
2. Connect GitHub repository
3. Build command: `pip install -r erp-dashboard/requirements.txt`
4. Start command: `cd erp-dashboard && gunicorn app:app`
5. Deploy and get your URL

Your app will be live at: `https://your-app-name.onrender.com`

---

## Recommended: Option 1 (Frontend on Netlify + Backend on Render)

This gives you:

- ✅ CDN-fast frontend
- ✅ Affordable backend hosting
- ✅ Easy scaling
- ✅ Great uptime

Both services have generous free tiers!
