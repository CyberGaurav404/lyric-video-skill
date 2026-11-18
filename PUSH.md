# Push this repo to GitHub

GitHub API se repo create karte waqt account suspended bataya gaya (403), isliye ye
folder tum khud push karo:

```bash
# 1) GitHub par khaali repo banao (README/gitignore ke bina):
#    https://github.com/new  ->  naam: lyric-video-skill  ->  Create repository

# 2) is folder ke andar:
git init
git add -A
git commit -m "Lyric video skill: Spotify-style and cinematic renderers, spec, samples"
git branch -M main
git remote add origin https://github.com/<your-username>/lyric-video-skill.git
git push -u origin main
```

Agar git identity set nahi hai:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```
