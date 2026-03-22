#!/bin/bash
chmod +x .github/tools/update_gh_pages_links.sh
cat .github/docs/README_base.md > README.md
echo ' ' >> README.md

echo "## Packages" >> README.md
echo " " >> README.md
echo " " >> README.md
echo "Links to the extended documentation of packaged modules, available through gh-pages:" >> README.md
echo " " >> README.md

.github/tools/update_gh_pages_links.sh >> README.md
