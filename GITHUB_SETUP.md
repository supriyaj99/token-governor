# Putting TokenGovernor on YOUR GitHub (the real link)

A GitHub link only exists once the code lives in a repo under your account. Here
is the exact ~15-minute process. Do this on the laptop that has the project.

## 1. Install Git (if you haven't)
Download from https://git-scm.com/download/win and install with all defaults.
Check it worked — in a terminal:
```powershell
git --version
```
You should see a version number.

## 2. Create an empty repo on GitHub
1. Sign in at https://github.com (make a free account if needed).
2. Click the **+** (top right) → **New repository**.
3. Name it `tokengovernor`. Leave it **empty** (don't add a README — you have one).
4. Choose **Public** (so recruiters can see it). Click **Create repository**.
5. Copy the URL it shows, e.g. `https://github.com/YOURNAME/tokengovernor.git`.

## 3. Turn your project folder into a repo and push it
Open a terminal **inside the `tokengovernor` folder** and run these one at a time.
(Each line explained after the `#`.)

```powershell
git init                         # start tracking this folder with Git
git add .                        # stage all files (the .gitignore excludes secrets/caches)
git commit -m "TokenGovernor: cost-aware LLM gateway (Modules 1-6 + benchmark)"   # save a snapshot
git branch -M main               # name the main branch 'main'
git remote add origin https://github.com/YOURNAME/tokengovernor.git   # link to your GitHub repo
git push -u origin main          # upload it
```

The first `git push` may pop up a GitHub sign-in — approve it in the browser.

## 4. Confirm
Refresh your GitHub repo page — all the files and the README should be there.
**That page's URL is your link.** Put it on your resume and LinkedIn.

## Notes
- `.env` and `*.db` are intentionally NOT uploaded (the `.gitignore` blocks them)
  — you never want secrets or local databases in a public repo.
- To push later changes: `git add .` → `git commit -m "what changed"` → `git push`.
- Learning Git itself is a resume skill — it's on nearly every job description.
