#! /bin/bash

cd ../acid/libs
# OpenSSL
ug --no-line-number -J6 -u -m 1 -o -a -i -U -P "openssl[ -]\d(\.\d){2}([a-z]|-alpha\d{1,2}|-beta\d|-pre\d)?" . > ../../openssl_meme/openssl_grep_libs.txt
sed -ri 's/openssl[ -]//I' ../../openssl_meme/openssl_grep_libs.txt
echo "OpenSSL done at $(date)"

# Jpeg-turbo (jpeg-turbo version 2.1.2 (build 20211216))
ug --no-line-number -J6 -u -m 1 -o -a -i -U "Jpeg-turbo version \d(\.\d+)+ \(build (\d{8})?\)" . > ../../openssl_meme/jpegturbo_grep_libs.txt
sed -ri 's/Jpeg-turbo version //I' ../../openssl_meme/jpegturbo_grep_libs.txt
echo "Jpeg turbo done at $(date)"

# FFmpeg (FFmpeg version 4.2)(ffmpeg-4.2.2)(FFmpeg version c3a1eb21)(FFmpeg version 332c5c1-4.3.1)
ug --no-line-number -J6 -u -m 1 -o -a -i -U "(ffmpeg-|FFmpeg version )([[:xdigit:]]{7}-?)?\d?(\.\d)*" . > ../../openssl_meme/ffmpeg_grep_libs.txt
sed -ri 's/(ffmpeg-|FFmpeg version )//I' ../../openssl_meme/ffmpeg_grep_libs.txt
# 332c5c1-4.3.1 -> 4.3.1 332c5c1 (import into DB format)
sed -ri 's/([[:xdigit:]]{7})-([0-9](\.[0-9]*)*)/\2 \1/I' ../../openssl_meme/ffmpeg_grep_libs.txt
# 43076c7 -> - 43076c7 (no version number exists, only commit hash)
sed -ri 's/:([[:xdigit:]]{7})$/:- \1/I' ../../openssl_meme/ffmpeg_grep_libs.txt
echo "ffmpeg done at $(date)"

# Firebase (Firebase C++ 6.16.1)
ug --no-line-number -J6 -u -m 1 -o -a -i -U "Firebase C\+\+ \d+(\.\d+)+" . > ../../openssl_meme/firebase_grep_libs.txt
sed -ri 's/Firebase C\+\+ //I' ../../openssl_meme/firebase_grep_libs.txt
echo "Firebase done at $(date)"

# Libavcodec (Lavc57.89.100)(can start with 6)
ug --no-line-number -J6 -u -m 1 -o -a -i -U "Lavc\d{2}(\.\d+)+" . > ../../openssl_meme/libavcodec_grep_libs.txt
sed -ri 's/Lavc//I' ../../openssl_meme/libavcodec_grep_libs.txt
echo "Libavcodec done at $(date)"

# Libavformat (Lavf57.89.100)(can start with 6)
ug --no-line-number -J6 -u -m 1 -o -a -i -U "Lavf\d{2}(\.\d+)+" . > ../../openssl_meme/libavformat_grep_libs.txt
sed -ri 's/Lavf//I' ../../openssl_meme/libavformat_grep_libs.txt
echo "Libavformat done at $(date)"

# Libavfilter (Lavfi7.87.100)(Lavfi10.x.x now also exists)
ug --no-line-number -J6 -u -m 1 -o -a -i -U "Lavfi\d{1,2}(\.\d+)+" . > ../../openssl_meme/libavfilter_grep_libs.txt
sed -ri 's/Lavfi//I' ../../openssl_meme/libavfilter_grep_libs.txt
echo "Libavfilter done at $(date)"

# Libpng (libpng version 1.6.36)(libpng version 1.6.38.git)(libpng version 1.6.35beta01)(libpng version 1.6.22rc01)(maybe a 0.99k exists ?)
ug --no-line-number -J6 -u -m 1 -o -a -i -U "Libpng version \d\.\d+(\.\w+)+" . > ../../openssl_meme/libpng_grep_libs.txt
sed -ri 's/Libpng version //I' ../../openssl_meme/libpng_grep_libs.txt
# 1.6.38.git -> 1.6.38-git and 1.6.35beta01 -> 1.6.35-beta01
sed -ri 's/([0-9](\.[0-9]*){2})(\.)?([[:alpha:]]+)/\1-\4/I' ../../openssl_meme/libpng_grep_libs.txt
echo "Libpng done at $(date)"

# Libglog (glog-0.3.5)
ug --no-line-number -J6 -u -m 1 -o -a -i -U "glog-[0-9]+(\.[0-9])*" . > ../../openssl_meme/libglog_grep_libs.txt
sed -ri 's/glog-//I' ../../openssl_meme/libglog_grep_libs.txt
echo "Libglog done at $(date)"

# Libvpx (WebM Project VP8 Encoder v1.5.0-794-gb2ccb9c)(WebM Project VP8 Decoder v1.3.0)
ug --no-line-number -J6 -u -m 1 -o -a -i -U "WebM Project VP[8-9] \w+ v\d(\.\d+){2}(-\w+)*" . > ../../openssl_meme/libvpx_grep_libs.txt
sed -ri 's/WebM Project VP[8-9] \w+ v//I' ../../openssl_meme/libvpx_grep_libs.txt
# Add space to make dashed part a comment
sed -ri 's/([0-9](\.[0-9]+)*)-(.*)/\1- \3/I' ../../openssl_meme/libvpx_grep_libs.txt
echo "Libvpx done at $(date)"

# OpenCV () 
ug --no-line-number -J6 -u -m 1 -o -a -i -U "opencv[\/ -][0-9]+(\.[0-9]+)+(-dev|-pre)?" . > ../../openssl_meme/opencv_grep_libs.txt
sed -ri 's/opencv[\/ -]//I' ../../openssl_meme/opencv_grep_libs.txt
echo "OpenCV done at $(date)"

# Speex
ug --no-line-number -J6 -u -m 1 -o -a -i -U "speex-\d(\.\d+)+((beta|rc)\d(\.\d)?)?" . > ../../openssl_meme/speex_grep_libs.txt
sed -ri 's/speex-//I' ../../openssl_meme/speex_grep_libs.txt
sed -ri 's/([0-9](\.[0-9]*)+)([[:alpha:]]+)/\1-\3/I' ../../openssl_meme/speex_grep_libs.txt
echo "Speex done at $(date)"

# SQLite3 ----- seems impossible to grep properly
# ug --no-line-number -J6 -u -m 1 -o -a -i "ˆ3\.([0-9]{1,}\.)+[0-9]" . > ../../openssl_meme/sqlite3_grep_libs.txt
# echo "SQLite3 done at $(date)"

# Unity3D -- recognizable until version 2017.x.xfx, before that is 5.x.xfx (too common)
ug --no-line-number -J6 -u -m 1 -o -a -i -U "(6000|20\d\d|Expected version: \d)(\.\d+){2}[fp]\d" . > ../../openssl_meme/unity3d_grep_libs.txt
sed -ri 's/(6000|20\d\d|Expected version: )//I' ../../openssl_meme/unity3d_grep_libs.txt
echo "Unity3D done at $(date)"

# Vorbis
ug --no-line-number -J6 -u -m 1 -o -a -i -U "Vorbis 1(\.\d+){2}" . > ../../openssl_meme/vorbis_grep_libs.txt
sed -ri 's/Vorbis //I' ../../openssl_meme/vorbis_grep_libs.txt
echo "Vorbis done at $(date)"

# XML2
ug --no-line-number -J6 -u -m 1 -o -a -i -U "GITv2\.\d+(\.\d{1,2})(-rc\d)?" . > ../../openssl_meme/xml2_grep_libs.txt
sed -ri 's/GITv\.//I' ../../openssl_meme/xml2_grep_libs.txt
echo "XML2 done at $(date)"

echo "All tasks completed at $(date)!"

