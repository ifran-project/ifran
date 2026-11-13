#!/bin/sh
find docs/tutorials -type f -name "*.ipynb" | while read -r file; do
    rel_dir=$(dirname "${file#docs/tutorials/}")
    out_dir="docs/tutorials/markdown/$rel_dir"
    mkdir -p "$out_dir"
    jupyter nbconvert --to markdown "$file" --output-dir "$out_dir"
done



find examples -type f -name "*.ipynb" | while read -r file; do
    rel_dir=$(dirname "${file#examples/}")
    out_dir="docs/examples/markdown/$rel_dir"
    mkdir -p "$out_dir"
    jupyter nbconvert --to markdown "$file" --output-dir "$out_dir"
done

