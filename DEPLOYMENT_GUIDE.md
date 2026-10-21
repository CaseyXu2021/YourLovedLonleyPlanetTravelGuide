# Deployment Guide - Share Your Travel App

## Quick Summary
Deploy your Streamlit app to **Streamlit Cloud** in 3 steps and get a public URL to share with anyone!

---

## Step 1: Prepare Your GitHub Repository

### 1.1 Create a GitHub Account
- Go to https://github.com
- Sign up for free

### 1.2 Create a New Repository
1. Click "+" (top right) → **New repository**
2. Name it: `lonely-planet-travel-app` (or any name)
3. **Make it Public**
4. **Do NOT** check "Add README" (you have files already)
5. Click **Create repository**

### 1.3 Push Your Code to GitHub
Open PowerShell in your project folder and run:

```powershell
# Initialize git (first time only)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Lonely Planet Travel App"

# Add GitHub remote (replace YOUR_USERNAME and lonely-planet-travel-app)
git remote add origin https://github.com/YOUR_USERNAME/lonely-planet-travel-app.git

# Set main branch and push
git branch -M main
git push -u origin main
```

**For password:** GitHub no longer accepts passwords. Instead:
1. Go to https://github.com/settings/tokens
2. Click **Generate new token** (classic)
3. Select scope: **repo**
4. Copy the token
5. Paste it when Git asks for password

---

## Step 2: Deploy on Streamlit Cloud (Free!)

### 2.1 Sign up on Streamlit Cloud
- Go to https://share.streamlit.io
- Click **Sign up with GitHub**
- Authorize Streamlit to access your GitHub

### 2.2 Deploy Your App
1. Click **New app**
2. **Repository**: select your repo (`YOUR_USERNAME/lonely-planet-travel-app`)
3. **Branch**: `main`
4. **Main file path**: `app_simplified_original.py`
5. **App URL**: Optional subdomain (e.g., `my-travel-app`)
6. Click **Deploy**

Wait 2-5 minutes. You'll get a public URL like:
```
https://lonely-planet-travel-app-xxxx.streamlit.app
```

### 2.3 Share Your App
Send this URL to anyone! They can use it in their browser without installing anything.

**Live URL of this project:**
```
https://yourloved-lonelyplanet-travelguide.streamlit.app
```
(custom subdomain set in app Settings → General → App URL)

---

## Step 3: Important Notes for Full Functionality

### Data Files Required
Your app needs these folders for full functionality:
- `knowledge_bases/` - Contains `.pkl` files with Lonely Planet data
- `book_picture/` - Contains destination photos
- `cover_picture/` - Contains cover images

**Options:**
1. **Push folders to GitHub** (if < 100 MB total)
   - Just include them in `git add .`
   
2. **Use Git LFS** for large files (> 100 MB)
   - Follow: https://git-lfs.github.com/
   
3. **Store separately** and document in README how to add them

### Secrets Management (Stay Safe!)
⚠️ **Never** push API keys or passwords to GitHub!

Currently, email credentials are hardcoded. Before sharing publicly, do this:

1. Create `.streamlit/secrets.toml` in your project:
```toml
[email]
sender = "katiexu0117@gmail.com"
password = "Ganbatte0117#"

[azure]
api_key = "<set AZURE_OPENAI_API_KEY in .streamlit/secrets.toml>"
```

2. Update `.gitignore`:
```
.streamlit/secrets.toml
.env
```

3. Update code to use secrets:
```python
SENDER_EMAIL = st.secrets["email"]["sender"]
SENDER_PASSWORD = st.secrets["email"]["password"]
```

4. In Streamlit Cloud settings:
   - App > Settings > Secrets
   - Paste your `secrets.toml` content

---

## Email Troubleshooting

### Issue: "Authentication failed"
**Solution:** Use Gmail **App Password**, not your account password
1. Go to https://myaccount.google.com/security
2. Find "App passwords" (bottom)
3. Select "Mail" and "Windows Computer" (or other device)
4. Generate 16-character password
5. Use this password in your code (spaces are automatically removed)

### Issue: "SMTP connection timeout"
**Solution:** Check firewall/internet
- Gmail SMTP might be blocked
- Use VPN if in restricted region

---

## Updating Your App

After deployment, to push changes:

```powershell
# In your project folder
git add .
git commit -m "Update: add new features"
git push
```

Streamlit Cloud automatically redeploys within 30 seconds!

---

## Sharing & Collaboration

### Share the URL
- Public link: `https://your-app.streamlit.app`
- Works on all devices/browsers
- No login required

### Collaborate
1. Add team members as GitHub collaborators
2. They can push changes, deploy their own versions
3. Or use GitHub branches for different versions

---

## Cost & Limits

**Free Tier:**
- ✅ Unlimited public apps
- ✅ 1 GB storage per app
- ✅ 1 CPU, 2 GB RAM
- 🔄 Shared resources (may be slow during peak hours)

**Pro Tier:**
- Dedicated resources
- Private apps
- Custom domains
- $5-10/month

---

## FAQ

**Q: Can I use my own domain?**
A: Yes, with Pro tier. Free tier uses `streamlit.app` subdomain.

**Q: How long until the app is live?**
A: Usually 2-5 minutes after deployment.

**Q: Can users modify the itinerary on my app?**
A: Yes, each user gets their own session. Changes don't affect others.

**Q: Is my data safe?**
A: Streamlit Cloud is secure. Don't push sensitive data (API keys, passwords) to GitHub!

---

## Next Steps

1. ✅ Create GitHub repository
2. ✅ Push your code
3. ✅ Deploy on Streamlit Cloud  
4. ✅ Share the URL
5. ✅ Monitor your app (Streamlit Cloud dashboard)

**Good luck! 🚀**
