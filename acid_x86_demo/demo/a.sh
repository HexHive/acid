







d=$(mktemp -d)
for f in bins/*; do strings -n 4 $f | sort > $d/$(basename $f) & done
wait

for f in $d/*; do 
	max=0
	file=0
	for g in $d/*; do 
		[[ $f == $g ]] && continue
		n=$(comm -12 $f $g | wc -l)
		((n>max)) && max=$n && file=$g
	done
	echo $f is closest to $file
done
