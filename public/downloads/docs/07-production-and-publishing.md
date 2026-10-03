# Rehearsal, draw.io editing and GitHub publication

## Deliver the talk

The main schedule is exactly 30 minutes across 16 slides, including brief interaction and the final panel handoff. Speak in English and display the English key takeaway on each slide. The script is a starting point; rehearse aloud at your own pace.

1. Build: `python3 scripts/build.py`.
2. Preview: `python3 -m http.server 8000 --directory _site --bind 127.0.0.1`.
3. Open `http://localhost:8000` from the Windows browser connected to WSL.
4. Choose **Start the 30-minute talk**.
5. Use Left/Right arrows, slide selection or navigation buttons.
6. Press **N** or choose **Speaker notes** to show notes. Press Esc to close.
7. Start the rehearsal timer explicitly; opening the deck does not start it. Closing pauses it.
8. Open the complete notes document in a second window for a separate presenter display.

Fullscreen depends on browser support. Presentation mode still works without it. Direct slide links use `#slide-4`, for example. The visible timer is local rehearsal timing, not an event clock or audience tracking.

The site also includes `print.html`, a complete 16-page printable deck. Use the browser’s Save as PDF option. After installing the browser-test dependency, `npm run export:pdf` creates a presentation PDF, speaker-notes PDF and preview screenshots in `_site/exports/`. These are generated local review artifacts; run the export again after changing content. The source-only ZIP remains portable without a PDF engine.

## Keep the performance reliable

The core presentation, local SVG diagrams and interactions use no CDN, AI API or server runtime. After building, `_site/index.html` can also be opened directly as a file. The local server is preferable for consistent browser behavior. Optional Mermaid rendering in document readers requires internet; code remains visible if rendering fails. The optional renderer loads a pinned Mermaid release only when clicked.

Before the event, verify projector readability, rehearse transitions, download the ZIP and keep a local copy of `_site`. Use the synthetic calculator briefly. If time is short, read its static example from the playbook. Avoid a live frontier-model demonstration that could introduce unpredictable latency, cost or unsupported facts.

## Open and edit draw.io artifacts

- `diagrams/presentation.drawio`: 16 editable pages, each at 1600 × 900 (16:9).
- `diagrams/research-flows.drawio`: 15 editable diagram pages.
- `diagrams/flows.md`: matching Mermaid source.
- `diagrams/*.svg`: portable offline diagram visuals.

Open the draw.io files with diagrams.net’s **File → Open from → Device** or the desktop application. Text, boxes and connectors are editable objects. Export individual pages or the complete presentation through the editor’s export function. The generated files are uncompressed XML for review and version control.

`content/talk.json` and `content/flows.json` are the canonical sources. The build regenerates speaker notes, evidence register, draw.io and SVG files. If you edit the draw.io deck manually, save it under a new name outside the generated filenames so your layout work survives the next build. Generated diagrams represent the talk’s explanatory structure; the full notes live in Markdown and the website.

## Repository structure

```text
content/             canonical talk data and flow definitions
docs/                preparation documents (01 and 08 are generated)
diagrams/            generated draw.io, Mermaid and SVG artifacts
site/                website template, styling and interactions
scripts/             build, validation and optional link checking
tests/               browser behavior tests
.github/workflows/   CI, manual Pages deployment and scheduled link audit
wave/                original repository material, preserved
_site/               generated website and public downloads, ignored by Git
```

The build uses only Python’s standard library. Browser tests use a pinned Playwright development dependency; website visitors need neither Node nor Python.

## GitHub Pages configuration

[GitHub Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site) describes plan eligibility: private-source Pages requires a supporting plan. Ordinary Pages sites can be publicly accessible even when their repository is private. This matters because the task began with a private repository. The public artifact is an explicit allowlist of generated talk documents, diagrams and site assets; the original PDF is not copied into it.

This package does not change repository visibility or upload the original PDF. To use an eligible private repository, keep its visibility and choose **Settings → Pages → Build and deployment → Source: GitHub Actions**. If the account plan does not support private-source Pages, use a separate public presentation repository after reviewing the publishable package. Do not make the original repository public merely to work around plan eligibility.

The deployment workflow is deliberately **manual**. CI validates pull requests and pushes; it does not publish their content automatically. When ready, run **Actions → Publish talk to GitHub Pages → Run workflow** on `main`. After a successful first deployment, GitHub reports the actual URL; the expected project URL is:

```text
https://pellera9.github.io/dutoaa_annual01/
```

That URL is a prediction based on the repository name, not a claim that the site is currently live. Subsequent publication is also a manual workflow run. See [GitHub’s custom workflow guide](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) for environment permissions and artifact deployment.

**Actual account check:** GitHub returned HTTP 422 when asked to enable Pages for the private `pellera9/dutoaa_annual01` repository: the current plan does not support Pages for this repository. The prepared fallback is a separate public site repository, `pellera9/dutoaa-ai-frontier-talk`, containing the generated presentation package. Its expected URL is `https://pellera9.github.io/dutoaa-ai-frontier-talk/`. The original source repository stays private. The fallback URL should be described as live only after deployment and HTTP verification.

**Publication result:** the separate [public presentation site](https://pellera9.github.io/dutoaa-ai-frontier-talk/) deployed successfully and its root URL was verified by HTTP on October 2, 2026. The private source repository’s GitHub validation workflow also passed. The public repo includes PDF exports under `public/exports/`; the private original PDF is absent. For future publication, prepare a new artifact with `python3 scripts/prepare_public_site.py --destination /path/to/new-empty-directory`, review it, update the public artifact repository and run its manual Pages workflow.

## Review and push from WSL

GitHub authentication was verified with network access during package preparation. A network-restricted sandbox can produce a misleading authentication failure. If authentication expires later, sign in interactively; never paste a token into the talk, source files or chat:

```bash
cd /home/wsun/work/dutoaa/dutoaa_annual01
gh auth login -h github.com
gh auth setup-git
python3 scripts/build.py
python3 scripts/validate.py
git diff --stat
git status --short
```

After reviewing the generated package, stage only the prepared files:

```bash
git add README.md .gitignore content docs diagrams scripts site tests package.json package-lock.json playwright.config.cjs .github/workflows
git commit -m "Prepare alumni AI discovery talk and interactive presentation"
git push origin main
```

Review any pre-existing files separately. The `wave/` and `claude_research/` directories were untracked before preparation and are not included in the staging command above. To preserve the PDF on GitHub, review its rights and stage it separately; the original local file remains untouched.

## Content updates

Edit canonical talk data for slide text, timing, notes, evidence labels and source metadata. Edit the other Markdown documents for research preparation. Run the build and validator. Run browser tests after changing interaction code. Commit the regenerated artifacts so that Markdown and draw.io readers see the same version. Publish only after reviewing the evidence-sensitive changes.

The weekly link-audit workflow checks accessibility of citation URLs and uploads a report. It never rewrites claims, publishes a new scientific headline or marks a source verified. This distinction is essential for a talk about rigorous adoption.
