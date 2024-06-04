#!/usr/bin/sh

OUT=data-out.zip

rm -f $OUT

# pack all *.out.* files
for f in $(ls ./data/*); do
    is_pdf_ext=$(echo $f | grep -Pc ".*\.out\.\w*$")
    if [ $is_pdf_ext -gt 0 ]; then
        echo "zip -r $OUT $f"
        zip -2 $OUT $f
    fi
done
