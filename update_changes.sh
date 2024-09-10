LN=$(grep -n '## Recent Changes' README.md | cut -d : -f 1)
let LN=LN+2
echo -n 'Enter text: '
read theline
sed -i "$LN i $theline" README.md
sed -i "3 i $theline" CHANGELOG.md
