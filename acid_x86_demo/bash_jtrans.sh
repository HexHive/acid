#!/bin/bash
set -euo pipefail
dir="/tmp/b"
mkdir -p $dir/a
find $dir -type f -print -delete

# extract ground_truth_libs subdir from droids.tar
tar xvf bash.tar -C $dir/a

for f in $dir/a/*; do strings -n 4 $f | sort > $dir/$(basename $f) & done;
wait 

find $dir/a -type f -print -delete
rmdir $dir/a

echo -n "{" > bash_out.json
for f in "$dir"/*; do
	(
    max_common_lines=0
    closest_file=""
    for g in "$dir"/*; do
        if [[ "$f" != "$g" ]]; then
            common_lines=$(comm -12 "$f" "$g" | wc -l)
            if [[ "$common_lines" -gt "$max_common_lines" ]]; then
                max_common_lines=$common_lines
                closest_file=$g
            fi
        fi
    done
    echo "$f is closest to $closest_file with $max_common_lines common lines" 
	echo -n "\"$(basename $f)\": [\"$(basename $closest_file)\"]," >> bash_out.json
	) &
done
wait

truncate -s -1 bash_out.json # remove last line of file
echo -n "}" >> bash_out.json
exit 1

d=/tmp/b;mkdir -p $d/a
find $d -type f -delete
tar xf bash.tar -C $d/a
for f in $d/a/*;do strings -n10 $f|sort>$d/${f##*/}&done
wait
rm -r $d/a
echo step\ one\ done
for f in $d/*;do(m=0;c=
for g in $d/*;do
[[ $f != $g ]]&&{n=$(comm -12 $f $g|wc -l);((n>m))&&m=$n&&c=$g;}
done
echo $f is closest to $c with $m common lines)&done
wait
