# Put the J2ME archive on GitHub Pages

Use the repository name **`j2me-archive`** so the supplied links match.

1. In **GitHub Desktop**, choose **File → New repository**. Enter `j2me-archive`. Leave the license selection at **None**. The package already supplies the README and `.gitignore`.
2. Choose **Repository → Show in Explorer**. Open the downloaded ZIP, then open its `j2me-archive` folder. Copy **the contents of that folder** into the repository folder. `index.html`, `README.md`, and `.nojekyll` should be directly inside the repository—not one extra folder down.
3. Back in GitHub Desktop, enter `Add J2ME archive` as the summary and **Commit to main**. Click **Publish repository**. Use a public repository for the intended public archive.
4. On GitHub, open **Settings → Pages**. Under **Build and deployment**, choose **Deploy from a branch**, select **main** and **/(root)**, then **Save**.
5. When GitHub reports the deployment is ready, open **https://wakkatobakka.github.io/j2me-archive/**. If an old page is cached, refresh it. On a phone, try a fresh tab or clear the site’s cached data.
6. In the repository’s **About** section, set Website to `https://wakkatobakka.github.io/j2me-archive/` and use this description:

> A source-linked J2ME game catalog with Wakka’s Omni recoveries, handset edition records, and a searchable research library.

The package includes all generated pages, metadata, and artwork. GitHub Pages needs no Python installation, JavaScript build tools, Actions workflow, or server setup.

## Updating the catalog later

The checked-in pages already work. For an intentional metadata update, edit the corresponding entries in `data/catalog.json` and source shards, then run:

```bash
python scripts/build.py
python scripts/validate.py
node scripts/check-search.cjs
```

`scripts/build.py` runs offline with Python’s standard library. It regenerates its own page directories. Keep hand-written changes in the generator, assets, or metadata, so a rebuild preserves them.

`assets/hero.svg` is the original phone illustration. `artwork/banner.svg` is the generated vector version of the PNG used by the README and social preview. Banner text is maintained in `scripts/render-banner.py`, which reads the phone art from `assets/hero.svg` and the entry count from the metadata. Run `python scripts/render-banner.py` to regenerate it; rendering the PNG requires Inkscape. That tool is not needed to build or host the site.

If using a different repository name, update `config.json`, the README’s project links, and this setup guide before rebuilding.
